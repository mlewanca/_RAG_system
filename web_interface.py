import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
from typing import Optional
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from config.roles import get_valid_roles, get_role_permissions, DOCUMENT_CATEGORIES

st.set_page_config(
    page_title="RAG System",
    page_icon="📚",
    layout="wide"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def init_session_state():
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None

def login_page():
    st.title("🔐 RAG System Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/auth/login",
                        json={"username": username, "password": password}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.username = username
                        
                        # Get user role from token
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        user_response = requests.get(
                            f"{API_BASE_URL}/api/auth/me",
                            headers=headers
                        )
                        
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            st.session_state.role = user_data.get("role", "service")
                            st.info(f"Debug: Retrieved role '{st.session_state.role}' for user {username}")
                        else:
                            # If /api/auth/me fails, set default role
                            st.session_state.role = "service"
                            st.warning(f"Could not fetch user details (status: {user_response.status_code}). Using default role. Response: {user_response.text}")
                        
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

def logout():
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

def upload_document_page():
    st.title("📤 Document Upload")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'md']
        )
        
        # Get allowed categories based on user role
        user_permissions = get_role_permissions(st.session_state.role or "service")
        
        if st.session_state.role == "admin":
            category_options = DOCUMENT_CATEGORIES
        else:
            category_options = user_permissions
        
        category = st.selectbox(
            "Document Category",
            options=category_options,
            disabled=(st.session_state.role not in ["admin"])
        )
        
        if st.session_state.role != "admin":
            st.info(f"As a {st.session_state.role} user, you can upload to: {', '.join(user_permissions)}")
        
        if uploaded_file is not None:
            if st.button("Upload Document", type="primary", use_container_width=True):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"category": category}
                    
                    with st.spinner("Uploading and processing document..."):
                        response = requests.post(
                            f"{API_BASE_URL}/api/documents/upload-file",
                            headers=headers,
                            files=files,
                            data=data
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Document '{result['filename']}' uploaded successfully!")
                        
                        with st.expander("Upload Details"):
                            st.json(result)
                    else:
                        st.error(f"Upload failed: {response.text}")
                except Exception as e:
                    st.error(f"Error uploading document: {str(e)}")
    
    with col2:
        st.info("""
        **Supported Formats:**
        - PDF documents
        - Text files (.txt)
        - Word documents (.docx)
        - Excel files (.xlsx)
        - Images (PNG, JPG, JPEG)
        - Markdown files (.md)
        """)

def query_interface_page():
    st.title("🔍 Query Documents")
    
    query = st.text_area(
        "Enter your query",
        placeholder="Ask any question about your documents...",
        height=100
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        top_k = st.number_input("Number of results", min_value=1, max_value=10, value=3)
    
    with col2:
        search_button = st.button("Search", type="primary", use_container_width=True)
    
    if search_button and query:
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            
            with st.spinner("Searching documents..."):
                response = requests.post(
                    f"{API_BASE_URL}/api/query",
                    headers=headers,
                    json={"query": query, "max_results": top_k}
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # The first result contains the generated answer
                if result.get("results") and len(result["results"]) > 0:
                    # Show improvement indicator if response was improved
                    if result.get('response_improved'):
                        st.success("✨ This response was improved using training data!")
                    
                    st.subheader("🤖 Answer")
                    answer_content = result["results"][0]["content"]
                    st.markdown(answer_content)
                    
                    # Store query info in session for potential feedback
                    st.session_state.last_query = {
                        'query': query,
                        'response': answer_content,
                        'feedback_id': result.get('feedback_id'),
                        'timestamp': result.get('timestamp')
                    }
                    
                    # Show source documents (skip the first which is the generated answer)
                    if len(result.get("results", [])) > 1:
                        st.subheader("📚 Sources")
                        for i, source in enumerate(result["results"][1:], 1):
                            source_name = source.get('metadata', {}).get('source', 'Unknown')
                            with st.expander(f"Source {i}: {source_name}"):
                                st.text(source.get("content", ""))
                                
                                metadata = source.get("metadata", {})
                                if metadata:
                                    st.caption("Metadata:")
                                    for key, value in metadata.items():
                                        st.caption(f"**{key}**: {value}")
                    
                    # Feedback section
                    st.divider()
                    st.subheader("📝 Feedback")
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        rating = st.select_slider(
                            "Rate this response:",
                            options=[1, 2, 3, 4, 5],
                            value=3,
                            format_func=lambda x: "⭐" * x
                        )
                    
                    with col2:
                        submit_feedback = st.button("Submit Feedback", type="secondary")
                    
                    feedback_text = st.text_area(
                        "Comments (optional):",
                        placeholder="What could be improved? Was this helpful?"
                    )
                    
                    expected_response = st.text_area(
                        "Better response (optional):",
                        placeholder="If you know a better answer, please share it here"
                    )
                    
                    # Submit feedback
                    if submit_feedback and st.session_state.get('last_query'):
                        if feedback_text.strip():  # Require some feedback text
                            try:
                                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                feedback_data = {
                                    "query": st.session_state.last_query['query'],
                                    "response": st.session_state.last_query['response'],
                                    "rating": rating,
                                    "feedback": feedback_text,
                                    "expected_response": expected_response if expected_response.strip() else None
                                }
                                
                                feedback_response = requests.post(
                                    f"{API_BASE_URL}/api/feedback",
                                    headers=headers,
                                    json=feedback_data
                                )
                                
                                if feedback_response.status_code == 200:
                                    st.success("✅ Thank you for your feedback! This will help improve the system.")
                                else:
                                    st.error(f"Failed to submit feedback: {feedback_response.text}")
                                    
                            except Exception as e:
                                st.error(f"Error submitting feedback: {str(e)}")
                        else:
                            st.warning("Please provide some feedback text before submitting.")
                else:
                    st.warning("No results found for your query.")
            else:
                st.error(f"Query failed: {response.text}")
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
    
    st.divider()
    
    st.subheader("Recent Queries")
    st.info("Query history will be displayed here in future versions.")

def admin_panel_page():
    st.title("👨‍💼 Admin Panel")
    
    if st.session_state.role != "admin":
        st.error("⛔ Access denied. Admin privileges required.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["User Management", "Document Management", "System Stats", "Training System"])
    
    with tab1:
        st.subheader("Create New User")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", get_valid_roles())
        
        with col2:
            if new_role:
                st.info(f"**Role Permissions:**\n{', '.join(get_role_permissions(new_role))}")
        
        if st.button("Create User", type="primary"):
            if new_username and new_password:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.post(
                        f"{API_BASE_URL}/api/users",
                        headers=headers,
                        json={
                            "username": new_username,
                            "password": new_password,
                            "role": new_role
                        }
                    )
                    
                    if response.status_code == 201:
                        st.success(f"User '{new_username}' created successfully!")
                    else:
                        st.error(f"Failed to create user: {response.text}")
                except Exception as e:
                    st.error(f"Error creating user: {str(e)}")
            else:
                st.warning("Please provide both username and password")
    
    with tab2:
        st.subheader("Document Categories")
        st.info("Document management features coming soon...")
    
    with tab3:
        st.subheader("System Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Documents", "N/A")
        with col2:
            st.metric("Total Queries", "N/A")
        with col3:
            st.metric("Active Users", "N/A")
    
    with tab4:
        st.subheader("🧠 Training System Management")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Training statistics
            if st.button("Refresh Training Stats", type="secondary"):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.get(f"{API_BASE_URL}/api/training/stats", headers=headers)
                    
                    if response.status_code == 200:
                        stats = response.json()
                        st.session_state.training_stats = stats
                    else:
                        st.error(f"Failed to get training stats: {response.text}")
                except Exception as e:
                    st.error(f"Error getting training stats: {str(e)}")
            
            if 'training_stats' in st.session_state:
                stats = st.session_state.training_stats
                
                st.subheader("📊 Feedback Statistics")
                
                feedback_stats = stats.get('feedback', {})
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.metric("Total Feedback", feedback_stats.get('total', 0))
                    st.metric("Processed", feedback_stats.get('processed', 0))
                
                with col_b:
                    st.metric("Avg Rating", f"{feedback_stats.get('avg_rating', 0):.1f}⭐")
                    st.metric("Positive Feedback", feedback_stats.get('positive', 0))
                
                st.subheader("🎯 Training Data")
                
                training_stats = stats.get('training_data', {})
                col_c, col_d = st.columns(2)
                
                with col_c:
                    st.metric("Training Pairs", training_stats.get('total_pairs', 0))
                
                with col_d:
                    st.metric("Avg Quality", f"{training_stats.get('avg_quality', 0):.1f}/5")
        
        with col2:
            st.subheader("🔄 Training Actions")
            
            # Process feedback button
            if st.button("Process Feedback to Training Data", type="primary"):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    
                    with st.spinner("Processing feedback..."):
                        response = requests.post(
                            f"{API_BASE_URL}/api/training/process-feedback",
                            headers=headers
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Processed {result['processed_count']} feedback entries!")
                    else:
                        st.error(f"Failed to process feedback: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error processing feedback: {str(e)}")
            
            st.markdown("---")
            
            # Export training data
            st.subheader("📤 Export Training Data")
            
            export_format = st.selectbox(
                "Export Format:",
                ["jsonl", "csv"],
                help="JSONL is preferred for model fine-tuning"
            )
            
            min_quality = st.slider(
                "Minimum Quality Score:",
                min_value=1.0,
                max_value=5.0,
                value=3.0,
                step=0.5,
                help="Only export training pairs with this quality or higher"
            )
            
            if st.button("Export Training Data", type="secondary"):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    
                    with st.spinner("Exporting training data..."):
                        response = requests.post(
                            f"{API_BASE_URL}/api/training/export",
                            headers=headers,
                            params={"format": export_format, "min_quality": min_quality}
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Training data exported to: `{result['output_file']}`")
                        st.info("You can now use this file for model fine-tuning with your preferred ML framework.")
                    else:
                        st.error(f"Failed to export training data: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error exporting training data: {str(e)}")
            
            st.markdown("---")
            
            # Training tips
            st.subheader("💡 Training Tips")
            st.info("""
            **How to improve your RAG system:**
            
            1. **Collect Feedback**: Users rate responses and provide corrections
            2. **Process Feedback**: Convert feedback into training data
            3. **Export Data**: Get training files for model fine-tuning
            4. **Monitor Quality**: Track improvement over time
            
            **Best Practices:**
            - Encourage users to provide detailed feedback
            - Process feedback regularly (weekly/monthly)
            - Focus on high-quality training pairs (>3.0 rating)
            - Use corrected responses for best results
            """)

def main():
    init_session_state()
    
    if st.session_state.token is None:
        login_page()
    else:
        st.sidebar.title("🚀 RAG System")
        st.sidebar.markdown(f"**User:** {st.session_state.username}")
        st.sidebar.markdown(f"**Role:** {st.session_state.role}")
        st.sidebar.divider()
        
        page = st.sidebar.radio(
            "Navigation",
            ["Query Documents", "Upload Document", "Admin Panel"]
        )
        
        st.sidebar.divider()
        
        if st.sidebar.button("Logout", use_container_width=True):
            # Call logout endpoint if token exists
            if st.session_state.token:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    requests.post(f"{API_BASE_URL}/api/auth/logout", headers=headers)
                except Exception:
                    pass  # Continue logout even if API call fails
            logout()
        
        if page == "Query Documents":
            query_interface_page()
        elif page == "Upload Document":
            upload_document_page()
        elif page == "Admin Panel":
            admin_panel_page()

if __name__ == "__main__":
    main()