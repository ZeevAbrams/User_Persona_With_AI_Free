# This is a 'basic', open-source version of the User Persona generator using LLMs
# It uses openAI's API, and requires a Key to use. On Streamlit, it uses my own key (my dime!)
# I tried to make it simpler, and therefore has few internal functions

import openai
import streamlit as st 
import streamlit.components.v1 as components
import time
import streamlit_antd_components as sac  # to create fancier UI https://nicedouble-streamlitantdcomponentsdemo-app-middmy.streamlit.app/



# DEF SECTION:
# find the key in the website: https://platform.openai.com/account/api-keys
openai.api_key = st.secrets["OPENAI_KEY"]
### REPLACE THIS COMMENT WITH YOUR API KEY - SUCH AS: openai.api_key = "sk-12345...10"

#os.getenv("OPENAI_API_KEY") # if you want to keep it here instead
MODEL_TO_USE = "gpt-3.5-turbo"  # we'll use the CHEAPER version - it works pretty well. Replace it with higher-end models if needed
COST_OF_MODEL = 0.002/1000  # for gpt 3.5 turbo https://openai.com/pricing This is OVERESTIMATING the price - price is cheaper for input tokens
TIME_TO_SLEEP = 3  # seconds
MAX_TRIES = 10  # putting a limit on the number of errors
temp_error = 0  # global to be added

local_test = True  # should have this as an argument to load

total_tokens_temp = 0  # holds the amount of total tokens used each time
approved_description = False
accept_customers = False
pm_system_prompt = {"role": "system", 
					"content": "You are a Product Manager working on defining the User Personas for your product."}
# this previous System Prompt is something that will ALWAYS be sent with your prompts - it's like a "start here" prompt

# force the background to be white
st.markdown(
		f"""
		<style>
		.reportview-container {{
			background-color: #FFFFFF;
		}}
		</style>
		""",
		unsafe_allow_html=True,
	)

# Streamlit is a finicky package that can't store variables easily. The solution is to put them into
# these session_state variables that ARE stored. In order to initialize them, I put them all here
if 'pressed_first_description' not in st.session_state:
	# setting all the saved states to zero
	st.session_state.pressed_first_description = False
	st.session_state['userP_proj_1liner_input'] = []
	st.session_state['userP_problem_description'] = []
	st.session_state.userP_accepted_problem = False
	st.session_state['userP_target_customers'] = ""
	st.session_state.userP_accepted_customers = False
	st.session_state['userP_good_persona'] = []
	st.session_state['userP_soso_persona'] = []
	st.session_state['userP_bad_persona'] = []
	st.session_state.finished_generating_personas = False
	# counters used at the end:
	st.session_state['userP_total_tokens'] = 0
	st.session_state['userP_rate_limit_ctr'] = 0



##### FUNCTION SECTION
# generate a response - using openAI, and checking for errors
# this function probably has redundant features since I originally wrote it
def generate_llm_response(messages_sent, wait_first=False, model_sent=MODEL_TO_USE):
	global temp_error

	# add in a pause, if calling sequentially
	if wait_first:
		time.sleep(TIME_TO_SLEEP)

	for attempt in range(1, MAX_TRIES+1):
		try:
			completion = openai.chat.completions.create(
				model=model_sent,
				messages=messages_sent
				# max_tokens=150  # for around 200 words
			)
			response = completion.choices[0].message.content
			total_tokens = completion.usage.total_tokens
			return response, total_tokens #, prompt_tokens, completion_tokens 
		
		except Exception as e:  # (openai.error.RateLimitError,openai.error.APIError)
			# something went wrong - need to try again, or write an error
			print("error: "+ str(e))
			if attempt < MAX_TRIES:
				time.sleep(TIME_TO_SLEEP * 2)  # or longer...

				temp_error = temp_error + 1  # update at the end
			else:
				# stop the program?
				st.markdown(""":red[Hit an error! Sorry, try generating a response from the beginning]""")
				break
	
def check_input_lengths(str_input, initial_state, max_length_chars = 250):
	# Streamlit has its own max_length checker, but I made my own
	if initial_state == True:
		if (len(str(str_input)) > max_length_chars):
			st.error('Length of input is too long', icon="🚨")
			return False
		if (len(str(str_input)) < 2):
			st.error('Please type something in the box', icon="❗")
			return False
		else:
			return initial_state

	

### Main Section
# Streamlit runs sequentially, and runs the entire script every time something is interacted with
	
# USER INPUT ON TOP:
st.header("User Persona Generator")
st.write(" ")
st.markdown(""":blue[This AI-template will make a User Persona for your product, as well as other User Persona variations.]""")

sac.divider(label="Define Project", icon="card-list", align='center', color='gray') # icon list https://icons.getbootstrap.com/
initial_user_input = st.text_area("What is the project/product you are working on, in roughly 1-line: [less than 250 characters]", 
							value = str(st.session_state['userP_proj_1liner_input']),
						  key='initial_input', height=80, max_chars=250)  # will reset

# m = st.markdown("""
# <style>
# div.stButton > button:first-child {
# 	background-color: rgb(224, 132, 27);
# }
# </style>""", unsafe_allow_html=True) 
# # This will make all buttons orange - just because I like it that way!

generate_Description = st.button(label="Generate Problem Description", key = "b_gen_description"
								 , help="Press here to regenerate")
generate_Description = check_input_lengths(initial_user_input, generate_Description)

# we only want to show subsequent sections if the buttons above them have been pressed, hence the session variables
if generate_Description:
	st.session_state.pressed_first_description = True
	st.session_state['userP_proj_1liner_input'] = initial_user_input
	# now we want to ZERO all the others - that way you can run this from the beginning
	st.session_state['userP_problem_description'] = []
	st.session_state.userP_accepted_problem = False
	st.session_state.userP_accepted_customers = False
	st.session_state['userP_good_persona'] = []
	st.session_state['userP_soso_persona'] = []
	st.session_state['userP_bad_persona'] = []
	st.session_state.finished_generating_personas = False

if st.session_state.pressed_first_description:
	# show everything below
	
	# We want to only Generate content (and spend money!) if the user pressed the button. Otherwise, when streamlit
	# runs the script, we want to have it simply display the content if it already has been generated

	if st.session_state['userP_problem_description'] == []:
		userP_initial_message = []
		userP_initial_message.append(pm_system_prompt)
		problem_description_prompt = "The project we are working on is described in one line as: " +\
			str(st.session_state['userP_proj_1liner_input']) + \
			"\n Write a 1-paragraph summary description of the PROBLEM this project will be solving. \
			The summary should be up to 80 words and should focus only on the Problem itself." 
		userP_initial_message.append({"role": "user", "content": problem_description_prompt})
		st.session_state['userP_problem_description'], tokens_this_response = generate_llm_response(userP_initial_message)
		total_tokens_temp += tokens_this_response

	# now display the result, and let the user edit it as well:
	edited_problem = st.text_area(label="Here is a short description of the Problem you are trying to solve. \
							   You can manually edit and press Enter when done", 
							   value = str(st.session_state['userP_problem_description']),
							   height=200, max_chars=800)
	
	st.write("Press 'Use this Problem' to accept this Problem description, or regenerate it from scratch by pressing \
		  'Generate Problem Description' above")
	
	approve_problem = st.button(label="Use this Problem", key="b_problem", help="Re-click to start again from here")
	approve_button = check_input_lengths(edited_problem, approve_problem, max_length_chars=800)

	if approve_button:
		st.session_state['userP_problem_description'] = edited_problem
		st.session_state.userP_accepted_problem = True
		# zero everything else:
		st.session_state.userP_accepted_customers = False
		st.session_state['userP_good_persona'] = []
		st.session_state['userP_soso_persona'] = []
		st.session_state['userP_bad_persona'] = []
		st.session_state.finished_generating_personas = False

# manually input the Customers:
if st.session_state.userP_accepted_problem:
	sac.divider(label="Target Customers", icon="people", align='center', color='gray') 

	st.write("List the Target Customers for your product")
	customer_input = st.text_input("Write up to 3 customers separated by commas", key='customer_input', max_chars=100
								, help="Example: Remote teams, freelancers, small businesses"
								, value=str(st.session_state['userP_target_customers']))
	accept_customers = st.button(label="Continue with these customers", key = "b_customers", help="Re-click to start again from here")
	accept_customers = check_input_lengths(customer_input, accept_customers, max_length_chars=100)
	
	if accept_customers:
		st.session_state.userP_accepted_customers = True
		st.session_state['userP_target_customers'] = customer_input
		# zero everything else:
		st.session_state['userP_good_persona'] = []
		st.session_state['userP_soso_persona'] = []
		st.session_state['userP_bad_persona'] = []
		st.session_state.finished_generating_personas = False

# Now for the bulk of the code - generate the User Personas

if st. session_state.userP_accepted_customers:
	sac.divider(label="User Personas", icon="person-badge", align='center', color='gray') 

	# only regenerate the content if needed
	if st.session_state['userP_good_persona'] == []:
		with st.spinner("Sequentially figuring out the Personas..."):
			# adds a spinner only when generating - note: this can be done in Parallel for speed
			
			# create messages for each persona, and add the prompt for each. There are only 3, so no functions are used
			initial_context_for_each = "The project is described as: " + str(st.session_state['userP_proj_1liner_input'] ) +\
				"\nA short description of the Problem being solved is: " + str(st.session_state['userP_problem_description']) + \
				"Your Target Customers for this product are: " + str(st.session_state['userP_target_customers']) + \
				"Write a User Persona for this product.\n"
			
			instruction_prompt_for_each = "\nFor the persona, make sure to list: \
				1. Their name 2. Overview, 3. Goals, 4. Behaviors, 5. Pains and 6. Needs \
				\n\nFor each of these 5 categories, write 3 short 1-line bullets."

			### Normal Persona
			good_persona_prompt =  initial_context_for_each + \
				"Assume the Persona is one of the listed target customers mentioned above."
			good_persona_prompt += instruction_prompt_for_each
			
			good_persona_msg = []
			good_persona_msg.append(pm_system_prompt)
			good_persona_msg.append({"role": "user", "content": good_persona_prompt})
			st.session_state['userP_good_persona'], tokens_this_response = generate_llm_response(good_persona_msg)
			total_tokens_temp += tokens_this_response

			### A little less likely Persona
			soso_persona_prompt = initial_context_for_each + \
				"Assume the Persona is one of the listed target customers mentioned above, \
				however, assume that it is a less-ideal customer who is less likely to like your product, \
				and it doesn't fit their needs 100%."
			# for somewhat better results, you can add the previous persona to the context:
			# soso_persona_prompt += "Here is an example of an Ideal persona, that I want this less-ideal customer \
			# 	to be different from: " + str(st.session_state['userP_good_persona'])
			soso_persona_prompt += instruction_prompt_for_each
			
			soso_persona_msg = []
			soso_persona_msg.append(pm_system_prompt)
			soso_persona_msg.append({"role": "user", "content": soso_persona_prompt})
			st.session_state['userP_soso_persona'], tokens_this_response = generate_llm_response(soso_persona_msg, wait_first=True)
			total_tokens_temp += tokens_this_response

			### A very skeptical customer
			bad_persona_prompt = initial_context_for_each + \
				"Write a User Persona for this product. Assume the persona is one of the listed target customers mentioned above, \
				however, assume that it is someone who is not at all likely to like your product, as they are skeptical, \
				and it doesn't fit their needs and pains." 
			# for somewhat better results, you can add the previous persona to the context:
			# bad_persona_prompt += "Here is an example of an Ideal persona, that I want this less-ideal customer \
			# 	to be different from: " + str(st.session_state['userP_good_persona'])
			# you could theoretically add the so-so persona as well to the context
			bad_persona_prompt += instruction_prompt_for_each

			bad_persona_msg = []
			bad_persona_msg.append(pm_system_prompt)
			bad_persona_msg.append({"role": "user", "content": bad_persona_prompt})
			st.session_state['userP_bad_persona'], tokens_this_response = generate_llm_response(bad_persona_msg, wait_first=True)
			total_tokens_temp += tokens_this_response

			st.session_state.finished_generating_personas = True

	# now print out the results:
	with st.container(border=True):  # puts it into a little box with a frame
		st.subheader("A Good Fit")
		st.write(str(st.session_state['userP_good_persona']))
	
	with st.container(border=True):
		st.subheader("A Little Less Likely")
		st.write(str(st.session_state['userP_soso_persona']))

	with st.container(border=True):
		st.subheader("A Harder Sell")
		st.write(str(st.session_state['userP_bad_persona']))


### Save to text
if st.session_state.finished_generating_personas:
	# you can copy paste everything, or download it as a text file (no formatting... in this open source solution ;)
	# We'll put all the info in the text file, just so you'll have everything too
	sac.divider(label="Text File Download", icon="filetype-txt", align='center', color='gray')
	
	st.markdown(""":blue[You can take everything from here directly using copy-paste, or you can download a simple TXT file with the data inside:]""")
	st.caption("Note that the formatting on some of the text files may not be perfect!")
	
	text_file = "User Persona Variations\n\nThe following is from the Iteraite template for your project.\n \
		\nContact info@iteraite.com for any questions and comments\n\n" + \
		"\nYour project 1-liner was: " + str(st.session_state['userP_proj_1liner_input'] ) +\
		"\n\nA short description of the Problem being solved was: " + str(st.session_state['userP_problem_description']) + \
		"\nYour Target Customers for this product are: " + str(st.session_state['userP_target_customers']) +\
		"\n\n" + \
		"Personas:\nA Good Fit:\n" + str(st.session_state['userP_good_persona']) + \
		"\n\nA Little Less Likely:\n" + str(st.session_state['userP_soso_persona']) + \
		"\n\nA Harder Sell:\n" + str(st.session_state['userP_bad_persona'])
	
	
	# give it a name with a timestamp:
	filename_date = time.strftime("%Y%m%d-%H%M%S")
	filename_txt = "UserPersona_" + filename_date + ".txt"
	st.download_button(label="Download TXT file", data=text_file, file_name=filename_txt)


#### End state
st.markdown("""---""")
st.session_state['userP_total_tokens'] = total_tokens_temp + st.session_state['userP_total_tokens']
cost_so_far = st.session_state['userP_total_tokens'] * COST_OF_MODEL
# this is a rough estimate - there is actually a difference between Input and Output costs for the model
st.session_state['userP_rate_limit_ctr'] = temp_error + st.session_state['userP_rate_limit_ctr']  # updates how many times it failed - maybe shouldn't save to session?

st.subheader("USAGE SUMMARY:")
st.write(f"Total # tokens:  {st.session_state['userP_total_tokens']}. Total cost: ${cost_so_far:.5f}. Total errors: {st.session_state['userP_rate_limit_ctr']}")
st.markdown("""The code to product this is open-sourced on [Github](https://github.com/ZeevAbrams?tab=repositories)""")
st.markdown("""
Created by [Iteraite](https://www.iteraite.com) | Contact: info@iteraite.com
""")
st.markdown(""":orange[To make this code/demo completely free, we have no tracking whatsoever - \
		   but would greatly appreciate it if you pinged us to tell us that you liked it, or try out our more complete] \
			[application](https://iteraite-applet-full-version.streamlit.app/)""")

	
