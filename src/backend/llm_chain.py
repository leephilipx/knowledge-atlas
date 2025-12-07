import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List

# Setup Models
# Ensure OPENAI_API_KEY is in env
llm = ChatOpenAI(temperature=0.3, model_name="gpt-4o-mini")

# --- Output Parsers ---
class ImageAnalysis(BaseModel):
    caption: str = Field(description="A detailed caption of the image")
    eli5: str = Field(description="Explain the image content like I am 5")
    tags: List[str] = Field(description="List of 5 relevant tags")

class TextAnalysis(BaseModel):
    summary: str = Field(description="A concise summary of the article")
    eli5: str = Field(description="Explain the topic like I am 5")
    tags: List[str] = Field(description="List of 5 relevant tags")

# --- Chains ---

def analyze_image_content(image_desc_text):
    """
    Since we are resizing images in processing, we'll assume we pass 
    a text description if using a multimodal model, OR 
    this function accepts the image bytes if using GPT-4V.
    For this modular example, we assume we have a way to describe it or 
    we are using a multimodal chain directly.
    """
    # Placeholder: In a real app, use HumanMessage with image_url for GPT-4V
    return {
        "caption": "Image analysis requires GPT-4V integration.", 
        "eli5": "This is a placeholder.", 
        "tags": ["image", "placeholder"]
    }

def analyze_text_content(text):
    parser = PydanticOutputParser(pydantic_object=TextAnalysis)
    
    prompt = PromptTemplate(
        template="""
        Analyze the following text content from a website:
        
        {text}
        
        {format_instructions}
        """,
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"text": text})
        return result.dict()
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "summary": "Error generating summary", 
            "eli5": "Error", 
            "tags": ["error"]
        }