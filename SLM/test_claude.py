import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="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",
)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(message.content)