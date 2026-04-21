import ollama

def generate_report(prompt: str, model="llama3.1"):
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response["response"]
    except Exception as e:
        print(f"Ollama çağrısı başarısız oldu: {e}")
        return f"Hata: {e}"
