Codex used the local Git CLI to run git clone over HTTPS. The first connection attempt failed because the shell lacked 
network access. Once the network permission for the session was granted, Git could reach GitHub and complete the clone 
without any GitHub token or password being used.