# 🧠 Memora
### Your AI-Powered Personal Knowledge Assistant

Memora is a personalized AI knowledge assistant that explores how persistent user memory can improve the relevance and personalization of AI-generated responses.

Unlike conventional AI assistants that may not retain personal context across interactions, Memora allows users to save important information, retrieve relevant memories, and use that context when asking questions.

**Live Demo:** https://memora-mzc7mrucxueuphaosxcdzm.streamlit.app/

**GitHub Repository:** https://github.com/rakshahv2004/Memora

---

## 🎯 Problem Statement

Most AI assistants generate responses based primarily on the current conversation. They may not consistently remember a user's interests, preferences, or previously shared information.

This creates an opportunity to explore whether persistent memory can make AI interactions more personalized and context-aware.

## 💡 Proposed Solution

Memora combines an AI assistant with a persistent memory system.

Users can:
- Save personal information and interests.
- Organize memories into categories.
- Ask questions using natural language.
- Generate responses using relevant saved memories.
- Explore relationships between concepts through a knowledge graph.
- Compare AI responses generated with and without memory.

## ✨ Key Features

### 1. AI Assistant
A conversational interface powered by Google's Gemini API that answers general questions and uses relevant saved memories to personalize responses.

### 2. Persistent Memory
Stores user-provided information in an SQLite database so it can be retrieved during future interactions.

### 3. Knowledge Graph
Uses AI-assisted entity and relationship extraction to explore connections between concepts stored in personal memories.

### 4. AI Evaluation Lab
Provides an experimental framework to compare:
- Memory ON responses.
- Memory OFF responses.
- Response relevance.
- Personalization.
- Accuracy.

### 5. Research Data Export
Supports exporting available experiment responses and human evaluation data for further analysis.

## 🔬 Research Motivation

**Research Question:**

Does access to persistent user memory improve the relevance and personalization of AI-generated responses?

Memora explores this question through a comparative evaluation framework.

The proposed methodology involves:

1. Preparing a set of evaluation questions.
2. Generating responses with memory enabled.
3. Generating responses with memory disabled.
4. Collecting human ratings for both responses.
5. Comparing relevance, personalization, and accuracy scores.

The evaluation framework is implemented, while larger-scale experiments and additional human ratings remain future work.

## 🏗️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Interactive web application |
| Google Gemini API | AI-powered response generation and information extraction |
| SQLite | Persistent memory and evaluation storage |
| NetworkX | Knowledge graph representation |
| PyMuPDF | PDF text extraction |
| Matplotlib | Data visualization |
| Pandas | Research data handling |

## 🧩 Project Architecture

```text
                 USER
                   |
                   v
             STREAMLIT UI
                   |
          +--------+--------+
          |        |        |
          v        v        v
       AI Chat  Memories  Evaluation
          |        |        |
          v        v        v
       Gemini    SQLite   SQLite
          |        |
          v        v
     Personalized  Memory
       Responses   Retrieval
                      |
                      v
                Knowledge Graph
                      |
                      v
                   NetworkX
```

## 📁 Project Structure

```text
Memora/
│
├── app.py
├── memory.py
├── knowledge_graph.py
├── evaluation.py
├── requirements.txt
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### Prerequisites
- Python 3.10 or later
- Google Gemini API key
- Git

### 1. Clone the repository

```bash
git clone https://github.com/rakshahv2004/Memora.git
cd Memora
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure the Gemini API key

Create a `.env` file in the project directory:

```env
GEMINI_API_KEY=your_actual_api_key
```

Never commit your API key or `.env` file to GitHub.

### 6. Run the application

```bash
streamlit run app.py
```

The application will open in your browser.

## ☁️ Deployment

Memora is deployed using Streamlit Community Cloud.

The deployed application requires a Gemini API key configured through Streamlit Cloud Secrets:

```toml
GEMINI_API_KEY = "your_actual_api_key"
```

## ⚠️ Current Limitations

- AI-generated responses and knowledge graph extraction depend on Gemini API availability and usage quotas.
- The current evaluation dataset is limited.
- Larger-scale human evaluation is still pending.
- The application currently does not provide multi-user authentication or user-specific database isolation.
- SQLite persistence on cloud hosting may require additional configuration for long-term storage.

## 🚀 Future Improvements

- More robust long-term memory retrieval.
- Semantic search using vector embeddings.
- Improved knowledge graph visualization.
- Larger and more diverse evaluation datasets.
- Blind human evaluation with more participants.
- Quantitative statistical analysis of experimental results.
- User authentication and isolated personal memory storage.
- Support for additional AI models.

## 👩‍💻 Author

**Raksha**

Memora is an independent project exploring personalized AI systems, persistent memory, knowledge representation, and evaluation of AI-generated responses.

---

*Built to explore the intersection of AI personalization, memory systems, and research-driven evaluation.*