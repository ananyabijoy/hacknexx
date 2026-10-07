AI Data Analyst:

Problem:

Working with messy CSV and Excel data can be difficult for people who don't know Python.

Even when someone asks a simple question like "What is the total revenue?", the data may have missing values, different number formats, duplicate records, or incomplete information.

Also, an AI can sometimes assume a value and give a confident but wrong answer.

 Our Solution:

We built an AI Data Analyst where users can upload CSV or Excel files and ask questions in normal language.

The AI understands the question and generates Python code to calculate the answer.

Instead of letting the AI directly give the numerical answer, we execute the generated Python code on the uploaded data. The user gets:

- The answer
- The Python code used
- An explanation/evidence for the answer

If the required information is not available, the system says that it cannot determine the answer instead of guessing.

 How It Works:

text
User
  ↓
Upload CSV / Excel
  ↓
Streamlit Interface
  ↓
Data Processing
  ↓
AI (Groq)
  ↓
Generate Python Code
  ↓
Execute Code on Data
  ↓
Answer + Code + Evidence
