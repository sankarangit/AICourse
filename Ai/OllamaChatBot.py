from ollama import chat

print("=" * 50)
print("Local AI Chat (type 'exit' to quit)")
print("=" * 50)

messages = []

while True:
    user_input = input("\nYou: ")

    if user_input.lower() in ["exit", "quit"]:
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    response = chat(
        model="llama3.2:3b",
        messages=messages
    )

    assistant = response["message"]["content"]

    print(f"\nAI: {assistant}")

    messages.append({
        "role": "assistant",
        "content": assistant
    })