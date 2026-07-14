import gradio as gr
from dotenv import load_dotenv

from utils.answer import answer_question

load_dotenv(override=True)


def format_context(context):
    result = "<h2 style='color: #ff7800;'>Relevant Context</h2>\n\n"
    for doc in context:
        result += f"<span style='color: #ff7800;'>Source: {doc.metadata['source']}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result


def chat(history):
    last_message = history[-1]["content"]
    prior = history[:-1]
    answer, context = answer_question(last_message, prior)
    history.append({"role": "assistant", "content": answer})
    return history, format_context(context)


def main():
    def put_message_in_chatbot(message, history):
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Insurellm Expert Assistant", theme=theme) as ui:
        gr.Markdown("# 🏢 Insurellm Expert Assistant\nAsk me about Insurellm's **products**, **employees**, **contracts**, or **company background**.")

        with gr.Row():
            with gr.Column(scale=1):
                WELCOME_MESSAGE = [
                    {
                        "role": "assistant",
                        "content": (
                            "👋 Hi! I'm the Insurellm Expert Assistant.\n\n"
                            "I can answer questions about:\n"
                            "- 🏢 **Company** — history, culture, and overview\n"
                            "- 🛡️ **Products** — Carllm, Homellm, Lifellm, Healthllm, Bizllm, Claimllm, Markellm, Rellm\n"
                            "- 👥 **Employees** — roles, compensation, and performance\n"
                            "- 📄 **Contracts** — client agreements, pricing, and SLAs\n\n"
                            "What would you like to know?"
                        ),
                    }
                ]
                chatbot = gr.Chatbot(
                    label="💬 Conversation",
                    height=600,
                    type="messages",
                    show_copy_button=True,
                    value=WELCOME_MESSAGE,
                )
                message = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g. What products does Insurellm offer?",
                    show_label=False,
                )
                gr.Examples(
                    examples=[
                        "What AI-powered insurance products does Insurellm offer?",
                        "Who is the CEO of Insurellm and what is their background?",
                        "What are the key terms of the contract with DriveSmart Insurance?",
                    ],
                    inputs=message,
                    label="Example Questions",
                )

            with gr.Column(scale=1):
                context_markdown = gr.Markdown(
                    label="📚 Retrieved Context",
                    value="*Retrieved context will appear here*",
                    container=True,
                    height=600,
                )

        message.submit(
            put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
