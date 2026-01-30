# Moth

Moth is a personal assistant powered by Google's Gemini 2.0 Flash model. It integrates directly with your Google Workspace account to help you manage emails, documents, files, calendar events, and more through a simple chat interface.

## ✨ Features

-   **Gmail**: Read unread emails, search messages, and send emails.
-   **Google Docs**: Create new documents and read existing ones.
-   **Google Drive**: List files and **delete files by name** (moves to trash).
-   **Google Calendar**: List upcoming events and create new ones.
-   **YouTube**: Search for videos.
-   **Web Search**: Perform general Google searches.
-   **Smart Logic**: Uses LangChain's tool-calling agent to intelligently decide which tools to use based on your requests.

## 🛠️ Setup

### Prerequisites

1.  **Python 3.10+** installed.
2.  **Google Cloud Project** with the following APIs enabled:
    -   Gmail API
    -   Google Docs API
    -   Google Drive API
    -   Google Calendar API
    -   YouTube Data API v3
3.  **`credentials.json`**: Download the OAuth 2.0 Client ID JSON file from your Google Cloud Console and place it in the project root.
4.  **Gemini API Key**: Get an API key from Google AI Studio.

### Installation

1.  Clone the repository and enter the directory.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

## 🚀 Usage

Run the Streamlit application:

```bash
streamlit run app.py
```

This will open the chat interface in your browser (usually at `http://localhost:8501`).

### Authentication
On the first run, a browser window will open asking you to log in with your Google account and grant permissions. A `token.json` file will be created to store your session locally.

## 💡 Examples

-   "What are my unread emails?"
-   "Draft a document called 'Project Plan' about AI agents."
-   "Delete the file 'Old Budget' from my Drive."
-   "Schedule a meeting with the team for Friday at 2 PM."
-   "Find a recipe for lasagna on YouTube."
