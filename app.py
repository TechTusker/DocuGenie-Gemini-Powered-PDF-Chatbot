import streamlit as st
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
#read the pdf go through each page of that pdf and we extract the text
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text+=page.extract_text()
    return text

#from pdf got the text, divided the text into chunks 
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks=text_splitter.split_text(text)
    return chunks

#converting those chunks retreived earlier into vectors
def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)

    # Save FAISS index
    save_path = "faiss_index"
    vector_store.save_local(save_path)
    
    # Verify if index was saved
    if not os.path.exists(save_path):
        raise ValueError("FAISS index was not saved properly!")
    
def get_conversational_chain():
    prompt_template = """
    You are an AI assistant with deep knowledge and analytical abilities. Answer the question in a detailed and structured manner.
    
    **Instructions:**
    - If the answer is in the provided context, give a **detailed explanation**.
    - If relevant, **break down complex concepts** into **simple steps**.
    - Use **examples and analogies** where appropriate.
    - Provide **extra insights or related information** if applicable.
    - If the answer is **not in the context**, say: "The answer is not available in the context."

    **Context:**
    {context}

    **Question:**
    {question}

    **Detailed Answer:**
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0.7)  # 🔥 Increased temperature for more explanation
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Check if FAISS index exists before loading
    if not os.path.exists("faiss_index"):
        st.error("FAISS index not found! Please upload and process PDFs first.")
        return

    try:
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True) 
        docs = new_db.similarity_search(user_question)
        chain = get_conversational_chain()
        response = chain(
            {"input_documents": docs, "question": user_question},
            return_only_outputs=True
        )
        st.write("Reply: ", response["output_text"])
    except ValueError as e:
        st.error(f"Error loading FAISS index: {e}")


#creating streamlit app
def main():
    st.set_page_config("Chat Docs")
    st.header("Chat with PDF")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Done")

if __name__ == "__main__":
    main()




