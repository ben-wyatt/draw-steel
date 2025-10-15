from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
from pydantic import BaseModel
from models.npcs import Monster
import json

load_dotenv()

def encode_image(image_path):
  """Encodes a local image file to a Base64 string."""
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode("utf-8")

image = encode_image("images/animal.png")



def main():
    client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"),base_url="https://openrouter.ai/api/v1")
    photo_response = client.beta.chat.completions.parse(
        model='openai/gpt-5',
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the contents of this image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image}"
                        },
                    },
                ],
            }
        ],
        response_format=Monster,
    )
    print(photo_response)

    print(photo_response.choices[0].message.parsed)
    result = {'full_response':photo_response}
    with open("output.json", "w") as f:
        json.dump(result, f)





if __name__ == "__main__":
    main()