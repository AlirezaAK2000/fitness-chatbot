# Fitness‑Chatbot

A fitness planning chatbot designed to assist users in creating, evaluating, and managing personalized workout routines.

---

## Features

- Allows users to interactively create customized fitness plans.
- Tracks the user progress.
- Built with modular components for easy extension.
- Evaluation capabilities via Jupyter notebooks to assess performance (`eval.ipynb`, `rag_eval.ipynb`).

---

## Requirements

- Python 3.9+  
- Required packages listed in `requirements.txt`, which may include Flask, transformers, langchain, and others for NLP and chatbot functionality.

## Setup & Installation


1. **Create and activate a virtual environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate   
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

    Here are the required API keys:
    - Taviliy 
    - Google API key
    - LLAMA cloud API key 

## Usage

1. **Run Flask application**
    ```bash 
    python app.py
    ```
2. **Run Chatbot**
    ```bash
    chainlit run chatbot.py
    ```


