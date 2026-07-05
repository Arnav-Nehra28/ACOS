import asyncio
import html
import os
import re
from typing import AsyncGenerator, List
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import get_script_run_ctx
from acos_client import AgentClient
from acos_models import ChatMessage, model_dump_compat, model_validate_compat


# A Streamlit app for interacting with the langgraph agent via a simple chat interface.
# The app has three main functions which are all run async:

# - main() - sets up the streamlit app and high level structure
# - draw_messages() - draws a set of chat messages - either replaying existing messages
#   or streaming new ones.
# - handle_feedback() - Draws a feedback widget and records feedback from the user.

# The app heavily uses AgentClient to interact with the agent's FastAPI endpoints.


APP_TITLE = "Agent Orchestration Studio"
APP_ICON = "🧭"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))
USER_AUTH_ENABLED = os.getenv("ENABLE_USER_AUTH", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

APP_TAGLINE = "Supervisor-routed LangGraph agents for RAG, web research, math, and knowledge graph reasoning."
FEATURE_CARDS = [
    ("Supervisor Graph", "Routes requests through safety, intent, rewrite, retrieval, response, and evaluation agents."),
    ("Hybrid Retrieval", "Combines Chroma vector search, BM25-style lexical matching, reranking, and local fallbacks."),
    ("Human Approval", "Pauses recency-sensitive web answers until the user approves or rejects the proposed search."),
    ("Ops Ready", "Includes auth, history, checkpoints, Prometheus metrics, Docker, Kubernetes, and CI/CD scaffolding."),
]
STARTER_PROMPTS = [
    ("Web Research", "latest breakthroughs in agentic AI orchestration in the last 7 days"),
    ("Local RAG", "local: summarize the uploaded project documents and list the key architecture decisions"),
    ("Knowledge Graph", "local: how are FastAPI, Streamlit, ChromaDB, and PostgreSQL connected in this system?"),
    ("Math Agent", "calculate the monthly cost if 12,500 requests cost 0.002 dollars each"),
]


def _extract_hitl_preview_context(text: str) -> dict | None:
    content = (text or "").strip()
    if not content:
        return None
    if "Human approval required before web-answer generation." not in content:
        return None

    # Support both single-line and multi-line render variants.
    query_match = re.search(
        r"Query:\s*(.+?)(?:\s+Recency target:\s*last\s*(\d+)\s+days|$)",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not query_match:
        return None

    query = (query_match.group(1) or "").strip()
    if not query:
        return None

    days_raw = query_match.group(2) or ""
    recency_days = int(days_raw) if days_raw.isdigit() else 0
    return {"query": query, "recency_days": recency_days}


def _history_rows_to_chat_messages(rows: list[dict]) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for row in reversed(rows or []):
        role = str(row.get("role") or "").strip()
        if role not in {"human", "ai", "tool"}:
            continue
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        messages.append(
            ChatMessage(
                type=role,  # type: ignore[arg-type]
                content=content,
                run_id=str(row.get("run_id") or "") or None,
            )
        )
    return messages


def _thread_label(thread: dict) -> str:
    thread_id = str(thread.get("thread_id") or "")
    count = int(thread.get("message_count") or 0)
    when = str(thread.get("last_message_at") or "")
    preview = str(thread.get("last_message_preview") or "").replace("\n", " ").strip()
    if len(preview) > 64:
        preview = preview[:61] + "..."
    when_short = when.replace("T", " ")[:19] if when else "-"
    if preview:
        return f"{when_short} | {count} msgs | {preview}"
    return f"{when_short} | {count} msgs | {thread_id}"


def _apply_app_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --studio-bg: #f7f9fc;
            --studio-panel: #ffffff;
            --studio-ink: #172033;
            --studio-muted: #647084;
            --studio-line: #dbe4ef;
            --studio-blue: #2563eb;
            --studio-teal: #0891b2;
            --studio-green: #16a34a;
            --studio-amber: #d97706;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 30rem),
                radial-gradient(circle at 85% 12%, rgba(8, 145, 178, 0.10), transparent 24rem),
                var(--studio-bg);
            color: var(--studio-ink);
        }

        .main .block-container {
            max-width: 1120px;
            padding-top: 1.75rem;
            padding-bottom: 6rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
            border-right: 1px solid var(--studio-line);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: var(--studio-muted);
        }

        .studio-hero,
        .studio-card,
        .studio-hitl {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--studio-line);
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
        }

        .studio-hero {
            padding: 1.35rem 1.45rem;
            margin-bottom: 1rem;
        }

        .studio-eyebrow {
            color: var(--studio-teal);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }

        .studio-title {
            color: var(--studio-ink);
            font-size: 2rem;
            font-weight: 750;
            line-height: 1.16;
            margin: 0 0 0.45rem;
        }

        .studio-subtitle {
            color: var(--studio-muted);
            font-size: 0.98rem;
            line-height: 1.55;
            max-width: 760px;
        }

        .studio-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.7rem;
            margin-top: 1rem;
        }

        .studio-metric {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem;
        }

        .studio-metric strong {
            color: var(--studio-ink);
            display: block;
            font-size: 0.94rem;
            margin-bottom: 0.15rem;
        }

        .studio-metric span {
            color: var(--studio-muted);
            font-size: 0.78rem;
        }

        .studio-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.85rem 0 1rem;
        }

        .studio-card {
            padding: 1rem;
        }

        .studio-card h3 {
            color: var(--studio-ink);
            font-size: 0.98rem;
            margin: 0 0 0.35rem;
        }

        .studio-card p {
            color: var(--studio-muted);
            font-size: 0.88rem;
            line-height: 1.48;
            margin: 0;
        }

        .studio-sidebar-title {
            color: var(--studio-ink);
            font-size: 1.08rem;
            font-weight: 750;
            margin-bottom: 0.15rem;
        }

        .studio-sidebar-subtitle {
            color: var(--studio-muted);
            font-size: 0.8rem;
            line-height: 1.45;
            margin-bottom: 0.9rem;
        }

        .studio-session-card {
            background: #ffffff;
            border: 1px solid var(--studio-line);
            border-radius: 8px;
            padding: 0.75rem;
            margin: 0.7rem 0;
        }

        .studio-session-card code {
            color: #334155;
            white-space: normal;
            word-break: break-all;
        }

        .studio-hitl {
            border-color: #f6c56f;
            box-shadow: 0 18px 45px rgba(217, 119, 6, 0.10);
            padding: 1rem;
            margin: 1rem 0;
        }

        .studio-hitl strong {
            color: #92400e;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
            padding: 0.35rem 0.55rem;
        }

        div[data-testid="stChatInput"] {
            border-top: 1px solid var(--studio-line);
            background: rgba(247, 249, 252, 0.92);
            backdrop-filter: blur(12px);
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            font-weight: 650;
        }

        .stButton > button:hover {
            border-color: var(--studio-blue);
            color: var(--studio-blue);
        }

        @media (max-width: 800px) {
            .studio-metrics,
            .studio-grid {
                grid-template-columns: 1fr;
            }
            .studio-title {
                font-size: 1.55rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_app_header(thread_id: str, message_count: int) -> None:
    escaped_title = html.escape(APP_TITLE)
    escaped_tagline = html.escape(APP_TAGLINE)
    st.markdown(
        f"""
        <div class="studio-hero">
            <div class="studio-eyebrow">LangGraph multi-agent control plane</div>
            <h1 class="studio-title">{escaped_title}</h1>
            <div class="studio-subtitle">{escaped_tagline}</div>
            <div class="studio-metrics">
                <div class="studio-metric"><strong>12 agents</strong><span>Supervisor-routed graph</span></div>
                <div class="studio-metric"><strong>{message_count} messages</strong><span>Current thread activity</span></div>
                <div class="studio-metric"><strong>RAG + KG</strong><span>Local evidence retrieval</span></div>
                <div class="studio-metric"><strong>Ops layer</strong><span>Auth, metrics, persistence</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_brand() -> None:
    escaped_title = html.escape(APP_TITLE)
    st.markdown(
        f"""
        <div class="studio-sidebar-title">{APP_ICON} {escaped_title}</div>
        <div class="studio-sidebar-subtitle">
            Route questions across safety, retrieval, web, math, response, and evaluation agents.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_session_card(thread_id: str) -> None:
    escaped_thread_id = html.escape(thread_id)
    st.markdown(
        f"""
        <div class="studio-session-card">
            <strong>Active Thread</strong><br />
            <code>{escaped_thread_id}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_welcome_panel() -> None:
    cards = "".join(
        f"""
        <div class="studio-card">
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(description)}</p>
        </div>
        """
        for title, description in FEATURE_CARDS
    )
    st.markdown(
        f"""
        <div class="studio-grid">
            {cards}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_prompt_starters() -> str | None:
    st.caption("Try a routed workflow")
    selected_prompt = None
    columns = st.columns(4)
    for index, (label, prompt) in enumerate(STARTER_PROMPTS):
        if columns[index].button(label, use_container_width=True):
            selected_prompt = prompt
    return selected_prompt


def _render_hitl_header(query: str) -> None:
    escaped_query = html.escape(query)
    st.markdown(
        f"""
        <div class="studio-hitl">
            <strong>Human approval required</strong><br />
            The graph prepared a recency-aware web workflow for:
            <code>{escaped_query}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_agent_client():
    agent_url = os.getenv("AGENT_URL") or os.getenv("API_BASE_URL", "http://localhost:8000")
    return AgentClient(agent_url)


def get_available_models() -> dict[str, str]:
    models: dict[str, str] = {}
    if os.getenv("OPENAI_API_KEY"):
        models["OpenAI GPT-4o-mini (streaming)"] = "gpt-4o-mini"
    if os.getenv("GROQ_API_KEY"):
        models["llama-3.1-70b on Groq"] = "llama-3.1-70b"
    return models


async def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        menu_items={},
    )

    # Hide the streamlit upper-right chrome
    st.html(
        """
        <style>
        [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
            }
        </style>
        """,
    )
    _apply_app_theme()
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    models = get_available_models()
    if not models:
        st.error(
            "No model API key found. Add OPENAI_API_KEY or GROQ_API_KEY to .env and restart Streamlit."
        )
        st.code("OPENAI_API_KEY=your_key_here\nGROQ_API_KEY=your_key_here")
        st.stop()

    agent_client = get_agent_client()
    if USER_AUTH_ENABLED:
        if "auth_user_id" not in st.session_state:
            st.session_state.auth_user_id = ""
        if "auth_token" not in st.session_state:
            st.session_state.auth_token = ""
        if "thread_summaries" not in st.session_state:
            st.session_state.thread_summaries = []
        if st.session_state.auth_token:
            agent_client.set_access_token(st.session_state.auth_token)

    ctx = get_script_run_ctx()
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = (getattr(ctx, "session_id", None) if ctx else None) or str(uuid4())
    thread_id = st.session_state.thread_id

    # Config options
    with st.sidebar:
        _render_sidebar_brand()
        if USER_AUTH_ENABLED:
            st.subheader("Account")
            if st.session_state.auth_user_id:
                st.success(f"Signed in: `{st.session_state.auth_user_id}`")
                col_new, col_refresh = st.columns(2)
                if col_new.button("New Chat"):
                    st.session_state.messages = []
                    st.session_state.thread_id = str(uuid4())
                    st.rerun()
                if col_refresh.button("Refresh"):
                    try:
                        threads_payload = await agent_client.alist_threads(limit=30)
                        st.session_state.thread_summaries = threads_payload.get("threads", [])
                        st.toast("Conversation list refreshed.")
                        st.rerun()
                    except Exception as e:
                        st.warning(f"Could not refresh history: {e}")

                thread_summaries = st.session_state.get("thread_summaries", [])
                thread_ids = [str(t.get("thread_id") or "") for t in thread_summaries if t.get("thread_id")]
                if thread_ids:
                    if st.session_state.thread_id not in thread_ids:
                        st.session_state.thread_id = thread_ids[0]
                    label_map = {
                        str(t.get("thread_id") or ""): _thread_label(t) for t in thread_summaries
                    }
                    selected_thread = st.selectbox(
                        "Conversation History",
                        options=thread_ids,
                        index=thread_ids.index(st.session_state.thread_id),
                        format_func=lambda tid: label_map.get(tid, tid),
                    )
                    if selected_thread != st.session_state.thread_id:
                        try:
                            history_payload = await agent_client.aget_store(selected_thread, limit=200)
                            st.session_state.thread_id = selected_thread
                            st.session_state.messages = _history_rows_to_chat_messages(
                                history_payload.get("messages", [])
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to load selected conversation: {e}")

                if st.button("Logout"):
                    st.session_state.auth_user_id = ""
                    st.session_state.auth_token = ""
                    st.session_state.messages = []
                    st.session_state.thread_summaries = []
                    if "thread_id" in st.session_state:
                        del st.session_state.thread_id
                    agent_client.set_access_token(None)
                    st.rerun()
            else:
                auth_mode = st.radio(
                    "Authentication",
                    options=["Login", "Register"],
                    horizontal=True,
                )
                auth_user_id = st.text_input("User ID", key="auth_user_id_input")
                auth_password = st.text_input("Password", type="password", key="auth_password_input")
                if st.button("Continue"):
                    try:
                        if auth_mode == "Register":
                            auth = await agent_client.aregister(auth_user_id, auth_password)
                        else:
                            auth = await agent_client.alogin(auth_user_id, auth_password)
                        st.session_state.auth_user_id = auth.user_id
                        st.session_state.auth_token = auth.access_token
                        agent_client.set_access_token(auth.access_token)

                        threads_payload = await agent_client.alist_threads(limit=30)
                        thread_summaries = threads_payload.get("threads", [])
                        st.session_state.thread_summaries = thread_summaries
                        if thread_summaries:
                            latest_thread_id = str(thread_summaries[0].get("thread_id") or "")
                            if latest_thread_id:
                                history_payload = await agent_client.aget_store(latest_thread_id, limit=200)
                                st.session_state.thread_id = latest_thread_id
                                st.session_state.messages = _history_rows_to_chat_messages(
                                    history_payload.get("messages", [])
                                )
                                st.success("Authentication successful. Loaded latest conversation history.")
                            else:
                                st.session_state.messages = []
                                st.session_state.thread_id = str(uuid4())
                                st.success("Authentication successful. Started a new conversation.")
                        else:
                            st.session_state.messages = []
                            st.session_state.thread_id = str(uuid4())
                            st.success("Authentication successful. Started a new conversation.")
                        await asyncio.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}")

            if not st.session_state.auth_user_id:
                st.info("Login or register to start chatting.")

        _render_session_card(thread_id)
        with st.popover(":material/settings: Settings"):
            m = st.radio("LLM to use", options=list(models.keys()))
            model = models[m]
            use_streaming = st.toggle("Stream results", value=True)
            st.caption("Web HITL runs inside backend graph (reply `approve` / `reject: reason`).")
        with st.popover(":material/policy: Privacy"):
            st.write("Prompts, responses and feedback in this app are anonymously recorded and saved to LangSmith for product evaluation and improvement purposes only.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    messages: List[ChatMessage] = st.session_state.messages

    if USER_AUTH_ENABLED and not st.session_state.auth_user_id:
        _render_app_header(thread_id, len(messages))
        _render_welcome_panel()
        st.stop()

    thread_id = st.session_state.thread_id
    _render_app_header(thread_id, len(messages))

    # Draw existing messages
    if len(messages) == 0:
        _render_welcome_panel()

    # draw_messages() expects an async iterator over messages
    async def amessage_iter():
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    async def _submit_user_query(input_text: str, display_text: str | None = None) -> None:
        shown = (display_text or input_text or "").strip()
        messages.append(ChatMessage(type="human", content=shown))
        st.chat_message("human").write(shown)
        try:
            if use_streaming:
                stream = agent_client.astream(
                    message=input_text,
                    model=model,
                    thread_id=thread_id,
                )
                await draw_messages(stream, is_new=True)
            else:
                response = await agent_client.ainvoke(
                    message=input_text,
                    model=model,
                    thread_id=thread_id,
                )
                messages.append(response)
                st.chat_message("ai").write(response.content)

            # Keep local thread summary fresh after successful send.
            if USER_AUTH_ENABLED and st.session_state.get("auth_user_id"):
                try:
                    threads_payload = await agent_client.alist_threads(limit=30)
                    st.session_state.thread_summaries = threads_payload.get("threads", [])
                except Exception:
                    pass
        except Exception as e:
            err = f"Request failed: {e}"
            st.chat_message("ai").error(err)
            messages.append(ChatMessage(type="ai", content=err))

    if len(messages) == 0:
        starter_prompt = _render_prompt_starters()
        if starter_prompt:
            await _submit_user_query(starter_prompt)
            st.rerun()

    pending_hitl = None
    if messages:
        latest = messages[-1]
        if latest.type == "ai":
            pending_hitl = _extract_hitl_preview_context(latest.content or "")

    if pending_hitl:
        with st.container():
            _render_hitl_header(pending_hitl["query"])
            reject_reason = st.text_input(
                "Reject reason (optional)",
                key="web_hitl_reject_reason_input",
                placeholder="Example: Please use only last 3 days and include Reuters.",
            )
            col_approve, col_reject = st.columns(2)
            approve_clicked = col_approve.button("Approve", key="web_hitl_approve_btn")
            reject_clicked = col_reject.button("Reject", key="web_hitl_reject_btn")

        if approve_clicked:
            await _submit_user_query("approve", display_text="approve")
            st.rerun()
        if reject_clicked:
            reason = (reject_reason or "").strip()
            reject_text = f"reject: {reason}" if reason else "reject"
            await _submit_user_query(reject_text, display_text="reject")
            st.rerun()

    input_text = st.chat_input("Ask the supervisor to plan, search, retrieve, calculate, or reason over local docs...")
    if input_text:
        await _submit_user_query(input_text)
        st.rerun()  # Clear stale containers

    # If messages have been generated, show feedback widget
    if len(messages) > 0 and st.session_state.last_message is not None and messages[-1].type == "ai":
        with st.session_state.last_message:
            await handle_feedback()


async def draw_messages(
        messages_agen: AsyncGenerator[ChatMessage | str, None],
        is_new=False,
    ):
    """
    Draws a set of chat messages - either replaying existing messages
    or streaming new ones.

    This function has additional logic to handle streaming tokens and tool calls.
    - Use a placeholder container to render streaming tokens as they arrive.
    - Use a status container to render tool calls. Track the tool inputs and outputs
      and update the status container accordingly.
    
    The function also needs to track the last message container in session state
    since later messages can draw to the same container. This is also used for
    drawing the feedback widget in the latest chat message.

    Args:
        messages_aiter: An async iterator over messages to draw.
        is_new: Whether the messages are new or not.
    """

    # Keep track of the last message container
    last_message_type = None
    st.session_state.last_message = None

    # Placeholder for intermediate streaming tokens
    streaming_content = ""
    streaming_placeholder = None

    # Iterate over the messages and draw them
    while msg := await anext(messages_agen, None):
        # str message represents an intermediate token being streamed
        if isinstance(msg, str):
            # If placeholder is empty, this is the first token of a new message
            # being streamed. We need to do setup.
            if not streaming_placeholder:
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                with st.session_state.last_message:
                    streaming_placeholder = st.empty()
            
            streaming_content += msg
            streaming_placeholder.write(streaming_content)
            continue
        if not isinstance(msg, ChatMessage):
            # Streamlit reloads and mixed module import paths can produce a
            # ChatMessage-like object from a different class identity.
            # Normalize to the local ChatMessage model instead of failing.
            try:
                if isinstance(msg, dict):
                    msg = model_validate_compat(ChatMessage, msg)
                else:
                    msg = model_validate_compat(ChatMessage, model_dump_compat(msg))
            except Exception:
                st.error(f"Unexpected message type: {type(msg)}")
                st.write(msg)
                st.stop()
        match msg.type:
            # A message from the user, the easiest case
            case "human":
                last_message_type = "human"
                st.chat_message("human").write(msg.content)

            # A message from the agent is the most complex case, since we need to
            # handle streaming tokens and tool calls.
            case "ai":
                # If we're rendering new messages, store the message in session state
                if is_new:
                    st.session_state.messages.append(msg)
                
                # If the last message type was not AI, create a new chat message
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                
                with st.session_state.last_message:
                    # If the message has content, write it out.
                    # Reset the streaming variables to prepare for the next message.
                    if msg.content:
                        if streaming_placeholder:
                            streaming_placeholder.write(msg.content)
                            streaming_content = ""
                            streaming_placeholder = None
                        else:
                            st.write(msg.content)

                    if msg.tool_calls:
                        # Create a status container for each tool call and store the
                        # status container by ID to ensure results are mapped to the
                        # correct status container.
                        call_results = {}
                        for tool_call in msg.tool_calls:
                            status = st.status(
                                    f"""Tool Call: {tool_call["name"]}""",
                                    state="running" if is_new else "complete",
                                )
                            call_results[tool_call["id"]] = status
                            status.write("Input:")
                            status.write(tool_call["args"])

                        # Expect one ToolMessage for each tool call.
                        for _ in range(len(call_results)):
                            tool_result: ChatMessage = await anext(messages_agen)
                            if not tool_result.type == "tool":
                                st.error(f"Unexpected ChatMessage type: {tool_result.type}")
                                st.write(tool_result)
                                st.stop()
                            
                            # Record the message if it's new, and update the correct
                            # status container with the result
                            if is_new:
                                st.session_state.messages.append(tool_result)
                            status = call_results[tool_result.tool_call_id]
                            status.write("Output:")
                            status.write(tool_result.content)
                            status.update(state="complete")

            # In case of an unexpected message type, log an error and stop
            case _: 
                st.error(f"Unexpected ChatMessage type: {msg.type}")
                st.write(msg)
                st.stop()


async def handle_feedback():
    """Draws a feedback widget and records feedback from the user."""

    # Keep track of last feedback sent to avoid sending duplicates
    if "last_feedback" not in st.session_state:
        st.session_state.last_feedback = (None, None)
    
    latest_run_id = st.session_state.messages[-1].run_id
    if not latest_run_id:
        return
    feedback = st.feedback("stars", key=latest_run_id)

    # If the feedback value or run ID has changed, send a new feedback record
    if feedback and (latest_run_id, feedback) != st.session_state.last_feedback:
        
        # Normalize the feedback value (an index) to a score between 0 and 1
        normalized_score = (feedback + 1) / 5.0

        agent_client = get_agent_client()
        if st.session_state.get("auth_token"):
            agent_client.set_access_token(st.session_state.auth_token)
        await agent_client.acreate_feedback(
            run_id=latest_run_id,
            key="human-feedback-stars",
            score=normalized_score,
            kwargs=dict(
                comment="In-line human feedback",
            ),
        )
        st.session_state.last_feedback = (latest_run_id, feedback)
        st.toast("Feedback recorded", icon=":material/reviews:")


if __name__ == "__main__":
    asyncio.run(main())
