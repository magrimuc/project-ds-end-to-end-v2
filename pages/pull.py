import streamlit as st
import subprocess

st.set_page_config(
    page_title="Git Pull & Restart",
    page_icon="🔄",
    layout="wide"
)

st.markdown('<div class="main-header">🔄 Git Pull & Daemon Restart</div>', unsafe_allow_html=True)
st.write("Performs a Git pull and restarts the Streamlit daemon on the server.")

if st.button("Update Project & Restart", type="primary"):
    with st.spinner("Performing update..."):
        # 1. cd & git pull
        try:
            st.info("Running 'git pull'...")
            # We execute in the correct working directory
            res_pull = subprocess.run(
                "git pull", 
                shell=True, 
                capture_output=True, 
                text=True, 
                cwd="/var/www/project-ds-end-to-end-v2"
            )
            st.code(f"Git Pull Output:\nStdout:\n{res_pull.stdout}\nStderr:\n{res_pull.stderr}")
        except Exception as e:
            st.error(f"Error during git pull: {e}")
            
        # 2. restart systemd service
        try:
            st.info("Restarting Streamlit service...")
            # Note: sudoers file must allow passwordless restart for www-data/running user:
            # www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart streamlit-schulbedarf.service
            res_restart = subprocess.run(
                "sudo systemctl restart streamlit-schulbedarf.service", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            if res_restart.returncode == 0:
                st.success("Success! The service is restarting. Please reload the page in a few moments.")
            else:
                st.error(f"Error restarting service (Exit code {res_restart.returncode}):\n{res_restart.stderr}")
                st.warning("⚠️ Please ensure that the Linux user running Streamlit is allowed to execute this command via sudo without password prompting.")
        except Exception as e:
            st.error(f"Error executing restart: {e}")
