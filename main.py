import os
import sys
import platform
import streamlit as st
import subprocess
import traceback
import google.generativeai as genai
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import shutil

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def generate_code(prompt, update_code_callback=None):
    prompt = f""" 
    You are an AI Python Coder, write python code for {prompt}, you must follow the given rules
    Rule 1. Remove ```python and ``` in the response.
    Rule 2. do not take variable input from user. 
    Rule 3. if asked for a plot use matplotlib.pyplot.subplots_adjust for full plot save at 'outputs/plot.png'
    Rule 4. if asked for files save in 'outputs' folder 
    """

    model = genai.GenerativeModel('gemini-pro')
    codesave = ""

    for response in model.generate_content(prompt):
        codesave += response.text
        if update_code_callback:
            update_code_callback(codesave)

    if codesave.strip():
        return codesave
    else:
        raise Exception("Error in code generation.")

def save_code(code, filename):
    try:
        count = 1
        while True:
            new_filename = f"{filename}{count}.py"
            code_dir = st.session_state.get("codes_dir", "codes")
            os.makedirs(code_dir, exist_ok=True)
            output_path = os.path.join(code_dir, new_filename)
            if not os.path.exists(output_path):
                with open(output_path, "w") as file:
                    file.write(code)
                return output_path
            count += 1
    except Exception as e:
        print(f"Error saving code: {e}")
        return None

def execute_code(code_file, language='python'):
    if language == "python":
        venv_python = os.path.join(os.environ.get('VIRTUAL_ENV'), 'Scripts', 'python.exe')
        output = subprocess.run([venv_python, code_file], capture_output=True, text=True)
        outputs_dir = st.session_state.get("outputs_dir", "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        return output.stdout, output.stderr
    else:
        return "Unsupported language.", None

def generate_response(prompt):
    try:
        generated_code = generate_code(prompt)
        if generated_code.startswith('```python'):
            generated_code = generated_code[10:]
        if generated_code.endswith('```'):
            generated_code = generated_code[:-3]
        
        filename = "code"
        saved_file = save_code(generated_code, filename)
        stdout, stderr = execute_code(saved_file)
        return generated_code, stdout, stderr
    except Exception as e:
        return f"Error: {e}", None, None

def main():
    st.title("Arc Analysis")
    prompt = st.text_area("Enter your question or prompt")
    generated_code = st.empty()
    code_output = st.empty()
    uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True)

    if "codes_dir" not in st.session_state:
        st.session_state["codes_dir"] = "codes"
    if "outputs_dir" not in st.session_state:
        st.session_state["outputs_dir"] = "outputs"
    if "inputs_dir" not in st.session_state:
        st.session_state["inputs_dir"] = "inputs"
    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None

    if uploaded_files:
        inputs_dir = st.session_state["inputs_dir"]
        os.makedirs(inputs_dir, exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = os.path.join(inputs_dir, uploaded_file.name)
            with open(file_path, "wb") as file:
                file.write(uploaded_file.getbuffer())
            st.session_state["uploaded_file"] = file_path
            prompt += f" The file '{uploaded_file.name}' has been added to the '{inputs_dir}' folder."
            st.success(f"Saved file: {uploaded_file.name}")

    if st.button("Generate Code"):
        if not prompt:
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("Generating code..."):
                plot_path = os.path.join(st.session_state["outputs_dir"], "plot.png")
                if os.path.exists(plot_path):
                    os.remove(plot_path)

                code, stdout, stderr = generate_response(prompt)
                generated_code.code(code, language="python")

                plot_path = os.path.join(st.session_state["outputs_dir"], "plot.png")
                if os.path.exists(plot_path):
                    st.image(plot_path, caption="Plot")
                    code_output = "Plot"
                else:
                    if not stdout:
                        code_output.code("No Output Received", language="text")
                    else:
                        code_output.code(stdout, language="text")
                        if "Error: " in stdout:
                            st.error("An error occurred while generating the plot.")

if __name__ == "__main__":
    main()