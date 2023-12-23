# Prompt History

### 1st Stage:

> The goal of this first attempt at a prompt was simply to see if an extracted text 
> from a pdf could give interesting results when run through GPT 3.5.


```python
template = """\
I will give you a text exported from a pdf. It might not be clean data.
It is the text extracted from an educational slide deck about a certain topic 
Here is a brief summary about the subject matter: {summary}.
Your task is to assist me in contextualising the slides so that it can be used
as an example for other people who might wish to create a similar slide for 
another educational slide deck, with a different topic.

You will get the text extracted from only one of the slides of this slide deck. 
I want you to use the text from this slide deck and assist me in summarising
this into key messages. You will not create more than {max_KM} key messages.
The key message should be related to the message that this slide serves in a
story line. The key message should not be a mere summary, it should be detached
from the specific content of the deck and generally focus on the kind of point
this slide is trying to make. 
For example: the key message a slide that shows positive growth of a company 
from Q1 to Q2 is not that the how much the company grew for, but rather that 
growth is happening. The key message of a slide listing many competitors is that
there is competition, the key message is not the names of the competitors.
each key message should not be longer than 5 words. If there are no relevant
key messages you will say 'No_KM'. 

You will structure an individual key message in the following way:

'Key Message 1: Growth is happening'

The text from the slide is {text_x}.

The key messages are:
"""

llm = OpenAI( )

summary = """\
Bukalapak.com Tbk, trading as Bukalapak, 
is an Indonesian e-commerce company. It was founded in 
2010 as an online marketplace to facilitate online commerce 
for small and medium enterprises (SME). Bukalapak later expanded 
to digitise small family-owned businesses, known in Indonesia as warungs.
"""
max_KM = 3

```

#### 1st output

from the following extracted text:

```
"Our Business Size Today Empowering individuals and SME s in IndonesiaBukalapakActive Access/sec100K+Inside Bukalapak Sellers4Mio+ Mitra Bukalapak500K+ Age 18 -3570% *data as per January 2019   Employer Branding Bukalapak  2019"
```

the prompt could get the following output from the LLM:

```
Key Message 1: Empowering individuals and SMEs
Key Message 2: Large business size
Key Message 3: Many partners and customers
```

This cost around 1cts in Open AI API fees

We also tried other LLMs over hosted on huggingface and got worse results.


### 2nd Stage:
> The goal of the second round prompt of was to get more targeted and specific output that can be
> deterministically used as data output. We want the output not just to be a list of text but rather
> a key:value system in JSON so that it can be input into a (graph) database. 


Sources:
https://www.youtube.com/watch?v=A6sIh-lmApk
https://github.com/tanchongmin/strictjson/blob/main/Strict_Text_(Strict_JSON_v2).ipynb

With the source above I found a way to make the output formatting more deterministic.
I struggled a little with making sure that the Key Messages were more generalistic. 
For example, when I used a more simple approach than the final result I would get the following 
Key Messages (more than 3):

```json
{'Key Message(s)': "[
'Empowering individuals and SMEs in Indonesia', 
'Active access to over 100K+', 
'Over 4 million sellers and 500K+ Bukalapak partners']"}
```

These Key Messages are obviously way too specific to be good Key Messages.

However, I made the following changes which yielded positive results:
1. with some prompt engineering I made the rules clearer. 
2. I changed the phrasing from "Key Messages" to "story point" since that is more exemplary of what I needed. However, this did not really change the output. 
3. The true breakthrough came when I decided to add a "Slide Title" and the "Slide Topic" to the output JSON and decided to include the following rule: "There should be no overlap between the story points and the slide title and slide topic."

> At this point it is also necessary to recognise that for payment reasons we changed from using 
> instructGPT to using GPT 3.5 turbo, which seems to be a lot cheaper and seems to yield similar performance with a better prompt.

This is the Prompt used at this stage:

```python
system_prompt = """\n
You are a categorisation agent.
Your task is to assist me in contextualising raw text extracted from slides.

You will get the text extracted from only one of the slides of a slide deck. 
I want you to use the text from this slide and assist me in summarising the 
the slide into its basic principles by understanding the stroypoint the slide conveys.

A story point  is represents the point a slide will make in a storyline. Slides 
with different topics should have the same abstract story points. 

These are the rules:
MOST IMPORTANT: the story points should never be specific. Keep them abstract.
Never use information in the story points that you think is specific to this slide deck.
VERY IMPORTANT: there should be no overlap between the story points and the slide title and slide topic.
1. You will under no circumstance create more than 3 story points.
2. The story point should be related to the message that this slide serves in a
story line. 
3. The story point should not be a mere summary, they should be detached
from the specific content of the deck and generally focus on the kind of point
this slide is trying to make.
5. The story points should not be longer than 5 words.
6. The story points will only be composed of of letters and numbers. NO SPECIAL CHARACTERS.
"""
```

Using the following prompting template:

```python
x = strict_text(system_prompt = system_prompt,
            user_prompt = text,
            output_format = {"Slide Title": "Give a Title to this slide", 
                             "Slide Topic": "Brief topic of this slide", 
                             "Story Point(s)": "[Story Point 1, Story Point 2, Story Point 3]"}
            )
```
#### Output

Yielded the following result:
```json
{
    'Slide Title': 'Our Business Size Today', 
    'Slide Topic': 'Empowering individuals and SMEs in Indonesia', 
    'Story Point(s)': "['Market presence', 'Large seller network', 'Target audience']"}
```

### 3rd Stage

We realised that there was a slight issue with the prompt. The prompt was formated to output a JSON format as follows appended to the prompt:

```
Formatting Rules:
No entity or relation should have more than 30 Characters. Ever.
Example Input: Growth is in market is strong and continuous.
Example Output: [["name.pdf", "hasTitle", "Growth Analysis"], ["name.pdf", "hasTopic", "Growth"], ["name.pdf", "hasStorypoint", "Continuous Growth"]]
Example Input: Company Inshabinti is learning how to leverage inbound sales
Example Output: [["name.pdf", "hasTitle", "Inshabinti sales approach"], ["name.pdf", "hasTopic", "Sales"], ["name.pdf", "hasStorypoint", "Changing Sales Approach"]]
```

However, this became slightly unpredictable due to the strctiness of JSON's formatting with regards to *quotemarks*.
Sometimes the output would be:


```
correct_format = '[["sample.pdf", "hasTitle", "Our Business Size Today"], ["sample.pdf", "hasTopic", "Business Size"], ["sample.pdf", "hasStorypoint", "Empowering Individuals and SMEs"], ["sample.pdf", "hasStorypoint", "Growing Quickly"], ["sample.pdf", "hasStorypoint", "Accessing New Markets"]]'

broken_format = "[['sample.pdf', 'hasTitle', 'Our Business Size Today'], ['sample.pdf', 'hasTopic', 'Business Size'], ['sample.pdf', 'hasStorypoint', 'Empowering Individuals and SMEs'], ['sample.pdf', 'hasStorypoint', 'Growing Quickly'], ['sample.pdf', 'hasStorypoint', 'Accessing New Markets']]"
```

Only the correct_format can be read by a knowledge graph plotter and transform the JSON data base into a knowledge graph reliably.

Update: i figured out a great bodge for this solution. 

First and fomremost, the new openai update to version >1.0.0 really messed with the "strictJSON". So i could either adapt this, but sadly I could not figure it out. So I had to conrol the version of openai installed to 0.28.1.

Then I figured I could just make sure that every string produced by the strictJSON by pushing it through a new "cleaner" function.

#Update

Ok I am still struggling with getting consistent output with JSON. Its not easy. I tried running the output through a second prompted OpenAI for a second round with the prompt:

```
f'format the following python dictionary into a json-like structure. Be accurate and do not make mistakes: {text}'
```

This worked, however, the output was now formatted as a string that when printed resembled a JSON file not actually a dictionary or JSON file that can be plugged into our graph plotter.

the real GPT out put looks like this and keeps an \n character for where there is a new line here.

"{
  "Knowledge Graph": [
    ["sample.pdf_4", "hasTitle", "Our Business Size Today"],
    ["sample.pdf_4", "hasTopic", "Business Size"],
    ["Business Size", "hasStorypoint", "Empowering Individuals"],
    ["Business Size", "hasStorypoint", "Empowering SMEs"],
    ["Business Size", "hasStorypoint", "IndonesiaBukalapak"]
  ]
}"

We need to either find a library that automatically does this transformation or do some clean up ourselves.


### 4th Stage

We ditched the strictJSON format as now open AI allows to format output as JSON.
I edited the prompt to show to more clearly reflect the way we want our knowledge graph to look:


```
system_prompt = '''\n
You are a knowledge graph builder.
Your task is to assist me in contextualising raw text extracted from slides into a Knowledge Graph through a JSON format.

The Slide Name is sample.pdf_4

You will get the text extracted from only one of the slides of a slide deck.
I want you to use the text from this slide and assist me in summarising
the slide into its basic principles by understanding the stroypoint the slide conveys.

For each slide there is a title and a topic. Each topic has between one and three story points.
A story point  is represents the point a slide will make in a storyline. Slides
with different topics should have the same abstract story points.

You are to output relations between two objects in the form [object_1, relation, object_2].

There are only three types of relations:
1. "hasTitle"
2. "hasTopic"
3. "hasStorypoint"

These are the rules:
MOST IMPORTANT: the story points should never be specific. Keep them abstract.
Never use information in the story points that you think is specific to this slide deck.
VERY IMPORTANT: there should be no overlap between the story points and the slide title and slide topic.
Never use information in the story points that you think is specific to this slide deck.
VERY IMPORTANT: there should be no overlap between the story points and the slide title and slide topic.
1. You will under no circumstance create more than 3 story points.
2. The story point should be related to the message that this slide serves in a
story line.
3. Do NOT INVENT NEW RELATIONS.
4. The story point should not be a mere summary, they should be detached
from the specific content of the deck and generally focus on the kind of point
this slide is trying to make.
5. The story points should not be longer than 5 words.
6. The story points will only be composed of of letters and numbers. NO SPECIAL CHARACTERS.


Formatting Rules:
No entity or relation should have more than 30 Characters. Ever.
Example Input: Growth is in market is strong and continuous.
Example Output: [["name.pdf", "hasTitle", "Growth Analysis"], ["name.pdf", "hasTopic", "Growth"], ["Growth", "hasStorypoint", "Continuous Growth"]]
Example Input: Company Inshabinti is learning how to leverage inbound sales
Example Output: [["name.pdf", "hasTitle", "Inshabinti sales approach"], ["name.pdf", "hasTopic", "Sales"], ["Sales", "hasStorypoint", "Changing Sales Approach"]]

```

Now it finally actually worked by using my own function.

#Final Version

We implemented an "initialiser prompt" that we obtained after an expert interview with a ML engineer at an undisclosed large German AI Lab.

We also included the Knowledge bases's Neo4J Schema, so that the AI will more easily create Cyphers that can input the slides into the knowledge graph.

```python
   prompt="""
    Ignore all previous instructions.

    1. you are to provide clear, concise and direct responses
    2. Eliminate unnecessary reminders, apologies, self-references and any pre-programmed niceties.
    3. Maintain a casual tone in your communication.
    4. Be transparent: if you're unsure about an answer or if a question is beyond your capabilities or knowledge, admit it.
    5. For any unclear or ambiguous queries, ask follow-up questions to undertand the user's intent better.
    6. When explaining concepts, use rea-world examples and analogies, where appropriate.
    7. For complete requests, take a deep breath and work on the problem step-by-step-
    8. For every response you will be tipped up to $200 (depending on the quality of your output).

    It is very important that you get this right. Multiple lives are at stake. 

    This is your goal. You are my assistant in analysing educational slides.
    You will get the raw text from a slide and extract important information.
    You will extract entities that contain the following information:

    1. Deck Name. The deck name is {deck_name}
    2. Slide Name. The slide name is {slide_name}
    3. Slide Title. A slide Title is simply what the slide calls itself.
    4. Slide Topic. A Slide Topic is a general brief summary of what the slide is about,
       it should be not longer than 5 words.
    4. Topic Storypoint A. A Storypoint is the point this slide is trying to bring
       across and how the slide tries to communicate the topic.
    5. Topic Storypoint B. A Storypoint is the point this slide is trying to bring
       across and how the slide tries to communicate the topic.

    It is important that you look at this neutrally and that the information is slide
    specific yet general enough that it can be related to more general queries to the knowledge graph.

    Return a JSON map of
            key: "query"
            value: a cypher query to add the knowledge graph to the graph database with the following Schema:

    Node properties are the following:
    DECK <name: STRING>,SLIDE <name: STRING>,TITLE <name: STRING, number: INTEGER>,
    TOPIC <name: STRING>,STORYPOINT <name: STRING>
    Relationship properties are the following:

    The relationships are the following:
    (:DECK)-[:hasSlide]->(:SLIDE),(:SLIDE)-[:hasTitle]->(:TITLE),
    (:SLIDE)-[:hasTopic]->(:TOPIC),(:TOPIC)-[:hasStorypoint]->(:STORYPOINT)
     """
```
