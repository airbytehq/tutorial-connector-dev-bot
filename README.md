# Connector dev bot

This is the code for the tutorial published on the Airbyte blog (link pending).

It implements a chat bot that uses contextual information stored in Pinecone, Langchain to orchestrate an LLM and the Slack sdk to provide a Slack bot that can answer Airbyte connector builder-related questions on Slack.

## How to run

You need locally installed python

* Follow the tutorial to create a Pinecone index and populate it with data via Airbyte
* Run `python -m venv venv` to create a virtual environment
* Run `source venv/bin/activate` to activate the virtual environment
* Run `pip install -r requirements.txt` to install the dependencies

### Run the bot locally in your terminal

* Run `export PINECONE_API_KEY=<your pinecone api key>` to set the pinecone api key
* Run `export PINECONE_INDEX_NAME=<your pinecone index name>` to set the pinecone index name
* Run `export PINECONE_ENV=<your pinecone env>` to set the pinecone env
* Run `export OPENAI_API_KEY=<your openai api key>` to set the openai api key
* Run `python localbot.py` to start the bot

### Run the bot on Slack

* Use the `slack_manifest.yml` file to create a Slack app and install it in your workspace.
* Run `export PINECONE_API_KEY=<your pinecone api key>` to set the pinecone api key
* Run `export PINECONE_INDEX_NAME=<your pinecone index name>` to set the pinecone index name
* Run `export PINECONE_ENV=<your pinecone env>` to set the pinecone env
* Run `export OPENAI_API_KEY=<your openai api key>` to set the openai api key
* Run `export SLACK_APP_TOKEN=<your slack app token>` to set the slack app token
* Run `export SLACK_BOT_TOKEN=<your slack bot token>` to set the slack bot token
* Run `python slackbot.py` to start the bot