import subprocess
import hashlib
import os


def open_interactive_ssh(host, user, key_path=None, password=None, options={"StrictHostKeyChecking": "no", "UserKnownHostsFile": "/dev/null"}, control_path_dir="~/.ssh", port=22):
    ssh_command = ["ssh", f"{user}@{host}"]

    # Specify the private key file if provided
    if key_path:
        ssh_command.extend(["-i", key_path, "-o", "PreferredAuthentications=publickey"])

    # Add SSH options
    if options:
        for key, value in options.items():
            ssh_command.extend(["-o", f"{key}={value}"])

    # Add ControlPath for persistent connections if specified
    if control_path_dir:
        control_path_dir = os.path.expanduser(os.path.expandvars(control_path_dir))
        pstring = "%s-%s-%s" % (host, port, user)
        m = hashlib.sha1()
        m.update(pstring.encode('utf-8'))
        digest = m.hexdigest()
        control_path = '%s/%s' % (control_path_dir, digest[:10])
        ssh_command.extend([
            "-o", "ControlMaster=auto",
            "-o", f"ControlPath={control_path}",
            "-o", "ControlPersist=60"
        ])

    try:
        if not key_path:
            sshpass_command = ["sshpass", "-p", password] + ssh_command
            subprocess.run(sshpass_command)
        else:
            # Run the SSH command normally (e.g., with SSH key or default setup)
            subprocess.run(ssh_command)
    except subprocess.CalledProcessError as e:
        print(f"SSH connection failed: {e}")
    except KeyboardInterrupt:
        print("\nConnection closed by user.")

