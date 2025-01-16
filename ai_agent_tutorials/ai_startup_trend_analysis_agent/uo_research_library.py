import os
import streamlit as st
from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.model.anthropic import Claude
from phi.tools.newspaper4k import Newspaper4k
from phi.tools import Tool
import logging
import sqlite3
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.DEBUG)

# Setting up Streamlit app
st.title("University of Oregon AI Grants Researcher 🎓")
st.caption("Discover AI grant opportunities and funding for curriculum enhancement and student learning initiatives.")

# Add sidebar tabs and API key input
tab_selection = st.sidebar.radio("View", ["Search Grants", "Saved Grants"])
anthropic_api_key = st.sidebar.text_input("Enter Anthropic API Key", type="password", key="api_key_input")

def init_database():
    conn = sqlite3.connect('saved_grants.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saved_grants
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  amount TEXT,
                  deadline TEXT,
                  source TEXT,
                  date_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_grant(title, description, amount, deadline, source):
    conn = sqlite3.connect('saved_grants.db')
    c = conn.cursor()
    c.execute('''INSERT INTO saved_grants (title, description, amount, deadline, source)
                 VALUES (?, ?, ?, ?, ?)''', (title, description, amount, deadline, source))
    conn.commit()
    conn.close()

def get_saved_grants():
    conn = sqlite3.connect('saved_grants.db')
    grants = pd.read_sql_query("SELECT * FROM saved_grants", conn)
    conn.close()
    return grants

init_database()

if tab_selection == "Search Grants":
    topic = st.text_input(
        "Enter specific AI education focus area:", 
        value="generative AI education grants funding opportunities Amazon Anthropic Microsoft",
        key="search_topic_input"
    )
    
    # Add unique key to the first Generate Analysis button
    if st.button("Generate Analysis", key="generate_analysis_button"):
        if not anthropic_api_key:
            st.warning("Please enter the required API key.")
        else:
            with st.spinner("Processing your request..."):
                try:
                    # Initialize Anthropic model
                    anthropic_model = Claude(id="claude-3-5-sonnet-20240620", api_key=anthropic_api_key)

                    # Define Research Librarian Agent
                    research_librarian = Agent(
                        name="Grants Researcher",
                        role="Researches grant opportunities and funding initiatives",
                        tools=[DuckDuckGo()],
                        model=anthropic_model,
                        instructions=[
                            "Search specifically for active grant opportunities and funding sources",
                            "Focus on websites like grants.gov, NSF.gov, ed.gov, and foundation websites",
                            "For each grant found, extract: title, description, amount, deadline, and source",
                            "Format each grant as a separate section with clear headers"
                        ],
                        show_tool_calls=True,
                        markdown=True,
                    )

                    # Define Summary Writer Agent (updated to use serp_tool)
                    summary_writer = Agent(
                        name="Grant Analyzer",
                        role="Analyzes and summarizes grant opportunities",
                        tools=[DuckDuckGo()],
                        model=anthropic_model,
                        instructions=["Provide detailed summaries of grant opportunities and requirements",
                                    "Highlight key deadlines, funding amounts, and eligibility criteria"],
                        show_tool_calls=True,
                        markdown=True,
                    )

                    # Define Trend Analyzer Agent (no tools needed for analysis)
                    trend_analyzer = Agent(
                        name="Opportunity Synthesizer",
                        role="Formats and analyzes grant opportunities",
                        model=anthropic_model,
                        instructions=[
                            "Format each grant opportunity as a separate section with clear headers",
                            "For each grant include: TITLE:, AMOUNT:, DEADLINE:, SOURCE:, DESCRIPTION:",
                            "Present opportunities in order of relevance and deadline",
                            "Focus only on current, open opportunities"
                        ],
                        show_tool_calls=True,
                        markdown=True,
                    )

                    # Step 1: Search for grants with more specific queries
                    search_queries = [
                        "NSF artificial intelligence education grants current",
                        "Department of Education AI grants funding opportunities",
                        "foundation grants generative AI education",
                        "university AI curriculum grants funding"
                    ]
                    
                    all_results = []
                    for query in search_queries:
                        research_response = research_librarian.run(
                            f"Search for and analyze grant opportunities using this search query: {query}. "
                            "Focus on finding specific grant programs, deadlines, and amounts. "
                            "Only include current or upcoming opportunities."
                        )
                        all_results.append(research_response.content)

                    combined_results = "\n\n".join(all_results)

                    # Step 2: Analyze grants
                    summary_response = summary_writer.run(
                        "Analyze and summarize these grant opportunities, focusing on the most relevant and current ones:\n" + 
                        combined_results
                    )
                    
                    # Step 3: Strategic analysis
                    trend_response = trend_analyzer.run(
                        f"Provide strategic analysis for these opportunities:\n{summary_response.content}"
                    )

                    # Display results with save buttons
                    st.subheader("Grant Opportunities")
                    
                    analysis_sections = trend_response.content.split("\n\n")  # Split analysis into sections by double newline

                    for section in analysis_sections:
                        if "TITLE:" in section:  # Only process sections that look like grant entries
                            # Extract grant details using string parsing
                            title = section.split("TITLE:")[1].split("\n")[0].strip() if "TITLE:" in section else ""
                            amount = section.split("AMOUNT:")[1].split("\n")[0].strip() if "AMOUNT:" in section else ""
                            deadline = section.split("DEADLINE:")[1].split("\n")[0].strip() if "DEADLINE:" in section else ""
                            source = section.split("SOURCE:")[1].split("\n")[0].strip() if "SOURCE:" in section else ""
                            description = section.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in section else ""
                            
                            # Create a columns layout for the grant and its save button
                            col1, col2 = st.columns([5,1])
                            
                            with col1:
                                st.markdown(f"### {title}")
                                st.markdown(f"**Amount:** {amount}")
                                st.markdown(f"**Deadline:** {deadline}")
                                st.markdown(f"**Source:** {source}")
                                st.markdown(f"**Description:**\n{description}")
                                
                            with col2:
                                # Generate a unique key for each save button
                                button_key = f"save_grant_{hash(title)}_{hash(deadline)}"
                                if st.button("Save Grant", key=button_key):
                                    try:
                                        save_grant(
                                            title,
                                            description,
                                            amount,
                                            deadline,
                                            source
                                        )
                                        st.success(f"Saved: {title}")
                                    except Exception as e:
                                        st.error(f"Error saving grant: {str(e)}")
                            
                            st.divider()  # Add a visual separator between grants

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Search details for debugging:", all_results if 'all_results' in locals() else "No results generated")
    else:
        st.info("Enter the topic and API keys, then click 'Generate Analysis' to start.")

elif tab_selection == "Saved Grants":
    st.title("Saved Grants Database 📊")
    
    saved_grants = get_saved_grants()
    if not saved_grants.empty:
        # Display grants in an expandable format
        for idx, grant in saved_grants.iterrows():
            with st.expander(f"{grant['title']} - Due: {grant['deadline']}"):
                st.write(f"**Amount:** {grant['amount']}")
                st.write(f"**Source:** {grant['source']}")
                st.write(f"**Description:**")
                st.write(grant['description'])
                st.write(f"*Saved on: {grant['date_saved']}*")
                
                # Add delete button
                if st.button(f"Delete Grant {grant['id']}", key=f"delete_{grant['id']}"):
                    conn = sqlite3.connect('saved_grants.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM saved_grants WHERE id=?", (grant['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Grant deleted successfully!")
                    st.experimental_rerun()
    else:
        st.info("No saved grants yet. Start searching and save interesting opportunities!")

    # Add export functionality
    if not saved_grants.empty:
        st.download_button(
            label="Export Grants to CSV",
            data=saved_grants.to_csv(index=False).encode('utf-8'),
            file_name="saved_grants.csv",
            mime="text/csv"
        )
