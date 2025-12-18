
# Project Startup Instructions

Follow these steps to run the project:

## Running on a Single System

1. Start the **auth** service on port `8000`.
2. Start the **chat** service on port `8001`.
3. Start the **stream** service on port `8002`.
4. Copy the custom `nginx.conf` from the `nginx/` directory and replace your system's default `nginx.conf` (make sure to back up the original so you can revert changes if needed).
5. Reload or restart Nginx.
	- Visit [http://127.0.0.1:3001](http://127.0.0.1:3001) to access the services.
	- You can also run on port `80` by changing the port setting in `nginx.conf`.

---

## Running on Cloud or Multiple Computers

1. Create a separate Nginx instance for each service.
2. It is recommended to set up the services in a virtual network with private access, so there are no public calls to these services.
3. Run each service on port `80`.
4. Implement a gateway to handle internal calls between services.
5. **Important:** Update the service URLs in the frontend to match your deployment.

---

**Note:**
- Always back up your original `nginx.conf` before making changes.
- Adjust ports and URLs as needed for your environment.