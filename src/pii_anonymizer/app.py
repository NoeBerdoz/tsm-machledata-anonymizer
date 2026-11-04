"""Local user interface. Start it with: uv run python -m pii_anonymizer"""

from time import perf_counter
from uuid import uuid4

import streamlit as st

from pii_anonymizer.engine import MODEL, answer, pseudonymize
from pii_anonymizer.feedback import save_feedback
from pii_anonymizer.files import FILE_TYPES, read_text


def rate(result: dict) -> None:
    stars = st.session_state[result["id"]]
    if stars is not None:  # None when the user removes the rating
        save_feedback(
            result["id"], stars + 1, result["pseudonymization_seconds"], result["response_seconds"]
        )


st.set_page_config(page_title="PII anonymizer")
st.title("PII anonymizer")
st.caption(f"Everything runs on this device, with {MODEL} through Ollama. Nothing is sent.")

prompt = st.text_area("Prompt", height=200)
uploads = st.file_uploader("Files", type=FILE_TYPES, accept_multiple_files=True)

if st.button("Pseudonymize and answer", type="primary"):
    st.session_state.pop("result", None)
    named_texts = [("Prompt", prompt)] if prompt.strip() else []
    for upload in uploads:
        try:
            text = read_text(upload.name, upload.getvalue())
        except Exception as error:  # each file library raises its own errors
            st.error(f"Could not read {upload.name}: {error}")
            st.stop()
        if text.strip():
            named_texts.append((upload.name, text))
        else:
            st.warning(f"No text found in {upload.name}. Scanned documents are not supported.")

    if not named_texts:
        st.warning("Write a prompt or attach a file first.")
        st.stop()

    try:
        start = perf_counter()
        with st.spinner("Looking for personal data..."):
            texts, mapping = pseudonymize([text for _, text in named_texts])
        pseudonymized = perf_counter()
        with st.spinner("Waiting for the response..."):
            # Only the texts: a file name can contain personal data too.
            response = answer("\n\n".join(texts))
    except (OSError, ValueError) as error:
        # Regex results alone would look complete, so nothing is shown.
        st.error(
            f"The local model could not finish, so nothing is shown: {error}\n\n"
            f"Check that Ollama is running and that the model is there: `ollama pull {MODEL}`"
        )
        st.stop()

    # Clicking a star reruns this page, so the result must outlive the click on the button.
    st.session_state["result"] = {
        "id": str(uuid4()),
        "names": [name for name, _ in named_texts],
        "texts": texts,
        "mapping": mapping,
        "response": response,
        "pseudonymization_seconds": pseudonymized - start,
        "response_seconds": perf_counter() - pseudonymized,
    }

if result := st.session_state.get("result"):
    st.subheader("Pseudonymized content")
    st.caption("Privacy boundary: only this content may leave the device.")
    for name, text in zip(result["names"], result["texts"], strict=True):
        st.text(name)
        st.code(text, language=None, wrap_lines=True)

    st.subheader("Response")
    st.caption(
        f"Response time: {result['response_seconds']:.1f} s. "
        f"Pseudonymization: {result['pseudonymization_seconds']:.1f} s. "
        "The placeholders are not restored yet."
    )
    # shortcut: Markdown can load remote images, remove them when real values are restored here
    st.markdown(result["response"])
    st.feedback("stars", key=result["id"], on_change=rate, args=(result,))

    st.subheader("Mapping table")
    st.caption("Stays on this device.")
    if result["mapping"]:
        rows = [
            {"Placeholder": key, "Real value": value} for key, value in result["mapping"].items()
        ]
        st.dataframe(rows, hide_index=True)
    else:
        st.info("No personal data found.")
