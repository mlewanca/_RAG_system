import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
from typing import Optional
import os

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
        
        category = st.selectbox(
            "Document Category",
            options=["service", "developer", "admin"],
            disabled=(st.session_state.role != "admin")
        )
        
        if st.session_state.role != "admin":
            category = "service"
            st.info(f"As a {st.session_state.role} user, documents will be uploaded to the 'service' category.")
        
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
                    st.subheader("🤖 Answer")
                    st.markdown(result["results"][0]["content"])
                    
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
    
    tab1, tab2, tab3 = st.tabs(["User Management", "Document Management", "System Stats"])
    
    with tab1:
        st.subheader("Create New User")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["service", "developer", "admin"])
        
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
            logout()
        
        if page == "Query Documents":
            query_interface_page()
        elif page == "Upload Document":
            upload_document_page()
        elif page == "Admin Panel":
            admin_panel_page()

if __name__ == "__main__":
    main()