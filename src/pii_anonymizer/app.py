"""Local user interface. Start it with: uv run python -m pii_anonymizer"""

from time import perf_counter
from uuid import uuid4

import streamlit as st

from pii_anonymizer.client import BACKEND_URL, ask_backend
from pii_anonymizer.engine import MODEL, pseudonymize, restore
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
st.caption(
    f"Personal data is found on this device, with the model {MODEL}. "
    f"Only the pseudonymized content goes to the backend ({BACKEND_URL})."
)

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
        if not text.strip():
            # Sending the request without this file would answer a different question.
            st.error(
                f"No text found in {upload.name}, so nothing was sent. Scanned documents "
                "are not supported: remove the file or attach its text."
            )
            st.stop()
        named_texts.append((upload.name, text))

    if not named_texts:
        st.warning("Write a prompt or attach a file first.")
        st.stop()

    try:
        start = perf_counter()
        with st.spinner("Looking for personal data..."):
            texts, mapping, missed = pseudonymize([text for _, text in named_texts])
        pseudonymized = perf_counter()
    except Exception as error:  # the model's libraries raise their own errors
        # Regex results alone would look complete, so nothing is shown and nothing is sent.
        st.error(
            f"The local model could not finish, so nothing was sent: {error}\n\n"
            "Check that PII_MODEL_DIR is the folder of the detection model (README)."
        )
        st.stop()

    restored, unknown = None, []
    # A value that the model found but could not place may still be readable in the texts.
    if not missed:
        try:
            with st.spinner("Waiting for the response..."):
                # Only the texts: a file name can contain personal data too.
                response = ask_backend("\n\n".join(texts))
        except OSError as error:
            st.error(
                f"The backend could not answer: {error}\n\n"
                "Check that it is running (`uv run python -m pii_anonymizer.backend`) and that "
                "PII_BACKEND_TOKEN is the same on both sides."
            )
            st.stop()
        restored, unknown = restore(response, mapping, texts)

    # Clicking a star reruns this page, so the result must outlive the click on the button.
    st.session_state["result"] = {
        "id": str(uuid4()),
        "names": [name for name, _ in named_texts],
        "texts": texts,
        "mapping": mapping,
        "missed": missed,
        "response": restored,
        "unknown": unknown,
        "pseudonymization_seconds": pseudonymized - start,
        "response_seconds": perf_counter() - pseudonymized,
    }

if result := st.session_state.get("result"):
    st.subheader("Pseudonymized content")
    st.caption("Privacy boundary: only this content may leave the device.")
    if result["missed"]:
        # The values go in st.code: st.warning renders Markdown, and a value comes from a model.
        st.warning(
            f"{len(result['missed'])} of the values found by the local model are not in the "
            "content as it wrote them, so they could not be hidden and nothing was sent. "
            "Rewrite or remove them, then try again."
        )
        st.code("\n".join(result["missed"]), language=None, wrap_lines=True)
    for name, text in zip(result["names"], result["texts"], strict=True):
        st.text(name)
        st.code(text, language=None, wrap_lines=True)

    if result["response"] is not None:
        st.subheader("Response")
        st.caption(
            f"Response time: {result['response_seconds']:.1f} s. "
            f"Pseudonymization: {result['pseudonymization_seconds']:.1f} s."
        )
        if result["unknown"]:
            st.warning(
                "The response contains placeholders that were never sent or that the model "
                "changed. "
                "They are shown as they are: "
                + ", ".join(f"`{token}`" for token in result["unknown"])
            )
        # Plain text: Markdown loads images by itself, so a response that ends with
        # ![](https://example.com/x.png?q=<PERSON_1>) would send the restored name without a click.
        st.code(result["response"], language=None, wrap_lines=True)
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
