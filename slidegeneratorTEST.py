# Importing the necessary Python libraries
import os
from dotenv import load_dotenv
import openai
from langchain.chains import GraphCypherQAChain
from langchain.chat_models import ChatOpenAI
from langchain.graphs import Neo4jGraph
import gradio as gr
import re
import json

#setup Environment Variables and APIs
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
neo4j_url = os.getenv("NEO4J_URL")
neo4j_username= os.getenv("NEO4J_USERNAME")
neo4j_password= os.getenv("NEO4J_PASSWORD")

graph = Neo4jGraph(
    url=neo4j_url, username=neo4j_username, password=neo4j_password)


## HELPER FUNCTIONS
# ---------------------------------------------------------------------------------------------------------------------


#this function is a langchain wrapper to neo4j and it for a schema. In this case, the default parameter matches slides to storypoints.
def context(graph_database, graph_database_schema="""
            MATCH (slide:SLIDE)-[:hasTopic]->(topic:TOPIC)-[:hasStorypoint]->(storypoint:STORYPOINT)
            RETURN slide.name AS SlideName, storypoint.name AS StorypointName;
            """):
     
     graph = graph_database
     schema = graph_database_schema
     context = graph.query(schema)
     return context

#since we use the "context" as a default parameter in other functions to be more efficient, we will define it now.
context = context(graph)

#this function will be used to turn the chat output into a list of PATHs that we can use to find the slide png files.
def png_path_finder(raw_text): #returns list of PATH strings
        text = raw_text

        try:
            #find the base folder:
            base_folder = 'C:/Users/heinr/code_projects/kg_project/slides_png/'
            
            # Use regular expression to find "deck" and extract the path            
            deck_matches = re.findall(r'deck_(\d{3})_slide_(\d{4})', text)

            # Construct the slide paths from the matches
            file_paths = [f'{base_folder}deck_{deck}_slide_{slide}.png' for deck, slide in deck_matches]
            
            file_path = file_paths[0]
            # Print the extracted file paths
            return file_path
        
        #minor error handling:
        except:
             print("Error: probably no file passed through. Try again.")


## MAIN FUNCTIONS
# ---------------------------------------------------------------------------------------------------------------------

#standard API Call to open AI with system prompt and user prompts.
def chat(system_prompt, user_prompt, model="gpt-3.5-turbo-1106", temperature=0):
    response = openai.chat.completions.create(
        model = model,

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}],
            temperature=temperature
            )
    res = response.choices[0].message.content
      
    return res

#this function formats the user input and links it to the chat history for further context awareness.
def format_chat_prompt(message, chat_history, max_convo_length):
    prompt = ""
    for turn in chat_history[-max_convo_length:]:
        user_message, bot_message = turn
        prompt = f"{prompt}\nUser: {user_message}\nAssistant: {bot_message}"
    prompt = f"{prompt}\nUser: {message}\nAssistant:"
    return prompt


#this is where the magic happens. this function takes a query then runs it through the context of the knowledge graph, identying which slides have storypoints most related to the query topic. 
#thus function returns a list of paths to the pngs of the slides so that gradio can search for those images and return them.
def respond(message, context=context):
        formatted_prompt = f"User:Please find slides related to {message}. Assistant:"
        system_prompt=f"""
        You have thes slides and storypoints as context: {context}
        You are a machine that is incredibly wise and very considerate and smart at connecting the dots between scarce information.
        Find the name of the slide with the storypoint that is most closely related to the message.
        before you decide take a deep breath and think about it. Be creative in how you abstract the connection between storypoint and the message.
        Only answer with the slide name that you find in the context. Nothing else. No nicities, salutations or confirmations.
        If you can't find one, try harder. Consider all slides. Only answer once you have considered every single slide.
        B
        consider all decks and only return the slide name as formatted in the context: deck_000_slide_0000
        """

        bot_message = chat(system_prompt = system_prompt, user_prompt = formatted_prompt)
        path = png_path_finder(bot_message)
        print(bot_message)
        return path

def slide_deck_storyline(storyline_prompt, nr_of_slides=5):
     nr_of_slides = str(nr_of_slides)
     system_prompt = f"""
     please give me a json map of {nr_of_slides} slides that you would include in a slide deck about {storyline_prompt}
     Only answer with the list. Do not include any nicities, greetings or repeat the task.
     Never make more than {nr_of_slides} slides. This is important
     Just give me the list. Keep the list concise and only answer with the list in this format.
     Name every key a slide (Slide 1, Slide 2 ... Slide N).
     The elements of the list should be storypoints, highlighting what the point the slide is trying to make is.
     """

     response = openai.chat.completions.create(
            model = "gpt-3.5-turbo-1106", 
            response_format = {"type": "json_object"},
            messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": storyline_prompt}],
            temperature=0
            )
     res = response.choices[0].message.content
     map = json.loads(res)
     pretty_list = "\n".join([f"⚡ {key}: {value}" for key, value in map.items()])
     slide_name_list = [map[key] for key in map]
     slide_name_nested = [slide_name_list]
     return map, slide_name_nested, pretty_list

#we need this function to turn the non iterable nested list that is gr.List into a simple list.
def iterator_for_gr(nested_list, i):
     #Initialize a variable to store the processing result
     slide_names = []

     #since the gr.List is a List[List] (nested list, we need to unwrap the 0th element)
     for item in nested_list[0]:
         slide_names.append(item)
         

     # Return a string that combines all the processed results
     return str(slide_names[i-1])


#we need this to go through the storyline and find the closest related slide for every topic.
def process_list_AI(nested_list, context=context):
     png_paths = [] #these are the paths to the pngs
     slide_nicknames = [] #these are the names the slide_deck_storyline gave the slides.
     nr = 0
     for i in nested_list[0]:
        res = respond(i, context)
        nr+=1
        slide_nicknames.append("Slide "+ str(nr))
        png_paths.append(res)
     png_paths_nested = [png_paths]
     return png_paths_nested, slide_nicknames

#create HTML versions of the slides (with bullet points)
def html_maker(message, temperature=1):
        formatted_prompt = f"User: Please create the HTML for slides related to {message}. only return the HTML code. HTML:"

        system_prompt3 = f"""Only answer in html. Nothing else. Give me the html code to for a slide on a 640x360 canvas. 
        The topic of the slide is {message}.
        I want the slide to be a pretty gradient colour and have a catchy action title and 3 bullet points on the left half 
        and in right half of the slide include a  large emoji that represents the slide. 
        the style.body ALWAYs needs to be left blank. it is the style.slide that needs the pretty colourful gradient.
        Also Add a footnote with tips on what kind visual communication device such as chart, graphs or images would be 
        best to drive home the point this slide is trying to make.
        Always make sure there is enough contrast between the slide colour and the text, better safe than sorry.
        Only respond with html no nicities or explanations.
        Make sure the slide looks nice and balanced.
        Everytime the slide is exceptionally beautiful you will be tipped 200$.
        Make sure it all fits into the slide, especially the text. Avoid making it too big. 
        Make sure there are no back ground colours that change the background of the browser window."""


        bot_message = chat(system_prompt = system_prompt3, user_prompt = formatted_prompt, temperature=temperature)
        return bot_message

#iterator version of html maker that creates a list for every generated slide.
def html_AI(nested_list):
     html_code = [] #these are the paths to the pngs
     slide_nicknames = [] #these are the names the slide_deck_storyline gave the slides.
     nr = 0
     items = str(len(nested_list[0]))
     for i in nested_list[0]:
        res = html_maker(i)
        nr+=1
        slide_nicknames.append("Slide "+ str(nr))
        html_code.append(res)
        print(f"...Completed ({nr}/{items})")
     html_code_nested = [html_code]
     return html_code_nested, slide_nicknames
     

## GRADIO UI LAYOUT & FUNCTIONALITY
## ---------------------------------------------------------------------------------------------------------------------

with gr.Blocks(title='Slide Inspo', theme='Soft') as demo:
     with gr.Row():
          with gr.Column(scale=1):
                gr.Markdown("# 1. Input: 🔍")
                storyline_prompt = gr.Textbox(placeholder = 'Give us a topic and we will provide a storyline for you! For example, try "Risk Management in Venture Capital', 
                                            label = 'Topic to build:',
                                            lines=5,
                                            scale = 3)
                nr_slides_to_build = gr.Number(value=5,
                                                label="How many slides?",
                                                scale =1)
                storyline_output_JSON = gr.JSON(visible=False)
                storyline_output_slide_name_list = gr.List(visible=False, type="array")
                btn = gr.Button("Build Storyline 🦄")

          with gr.Column(scale=1):
               gr.Markdown("# 2. Storyline: 🦄")
                            
               storyline_output_pretty = gr.Textbox(label="Your Storyline:", lines=13, scale=3)
               submit_button = gr.Button("⚡ Find Slides ⚡")

               btn.click(slide_deck_storyline, 
                                        inputs = [storyline_prompt, nr_slides_to_build], 
                                        outputs = [storyline_output_JSON, storyline_output_slide_name_list, storyline_output_pretty])
                
               storyline_prompt.submit(slide_deck_storyline, 
                                        inputs = [storyline_prompt, nr_slides_to_build], 
                                        outputs = [storyline_output_JSON, storyline_output_slide_name_list, storyline_output_pretty])

          with gr.Column(scale=3):
               gr.Markdown("# 3. Output: ⚡⚡  ")
               data = storyline_output_slide_name_list
               see_slide = gr.Number(label="See Slide Number: ", precision=0, value=1)
               gr.Markdown("⚡ Your Beautiful Slide: ")

               #now apply respond to everything in the list.
               htmls = gr.List(interactive=False, visible=False) #this is a list of png paths
               nicknames = gr.Radio(type="index", visible=False)
               html_box = gr.HTML()
               clear = gr.ClearButton(components=[storyline_prompt, 
                                                          nr_slides_to_build, 
                                                          storyline_output_JSON,                                         
                                                          storyline_output_slide_name_list,
                                                          storyline_output_pretty,
                                                          html_box,
                                                          see_slide,
                                                          data, html_box, nicknames,
                                                          ],

                                                          value="🧨 Clear 🧨",
                                                          )
               submit_button.click(html_AI, inputs=[data], outputs=[htmls, nicknames])
               see_slide.input(iterator_for_gr, inputs=[htmls, see_slide], outputs=[html_box])

gr.close_all()
demo.launch(share=True)
