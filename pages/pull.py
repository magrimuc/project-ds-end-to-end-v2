import streamlit as st
import subprocess

st.set_page_config(
    page_title="Git Pull & Restart",
    page_icon="🔄",
    layout="wide"
)

st.markdown('<div class="main-header">🔄 Git Pull & Daemon Restart</div>', unsafe_allow_html=True)
st.write("Führt einen Git Pull und einen Neustart des Streamlit-Dienstes auf dem Server aus.")

if st.button("Projekt aktualisieren und neu starten", type="primary"):
    with st.spinner("Führe Aktualisierung aus..."):
        # 1. cd & git pull
        try:
            st.info("Führe 'git pull' aus...")
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
            st.error(f"Fehler bei git pull: {e}")
            
        # 2. restart systemd service
        try:
            st.info("Starte Streamlit-Dienst neu...")
            # Note: sudoers file must allow passwordless restart for www-data/running user:
            # www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart streamlit-schulbedarf.service
            res_restart = subprocess.run(
                "sudo systemctl restart streamlit-schulbedarf.service", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            if res_restart.returncode == 0:
                st.success("Erfolgreich! Der Service wird neu gestartet. Bitte laden Sie die Seite in Kürze neu.")
            else:
                st.error(f"Fehler beim Dienst-Neustart (Exit-Code {res_restart.returncode}):\n{res_restart.stderr}")
                st.warning("⚠️ Bitte stellen Sie sicher, dass der Linux-Benutzer, unter dem Streamlit läuft, diesen Befehl ohne Passworteingabe per `sudo` ausführen darf.")
        except Exception as e:
            st.error(f"Fehler bei der Ausführung des Neustarts: {e}")
