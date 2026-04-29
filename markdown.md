I want to build a frontend for my app called "lifelikegame".

This is a gamified life management system.

The backend is already built using FastAPI, and I will connect via REST APIs.

Now I want you to help me design the frontend UI and structure using React.

Important!! all build in frontend folder, don't change anything in backend folder
---

🧠 App Concept:

Users manage their life like a game.

They have:

* Goals (long term)
* Tasks (under goals)
* Task Instances (daily generated tasks)
* Points (earned by completing tasks)

---

🎯 Main Pages:

1. Dashboard (Home)

* Show today's task instances
* Each task can be marked as done
* When marking done, user selects completion level (below just example):

  * perfect
  * normal
  * minimal
* Show points earned

2. Goals Page

* List all goals
* Each goal contains tasks

3. Create Task Flow

* Form to create a task
* Includes:

  * title
  * scoring scheme selection
  * schedule setup (daily / weekly / specific days)

4. Rewards Page

* Show current balance
* Show Rewards(item and require point)

5. Scoring Schemes
* CRUD function, such as perfect: 3, good: 2, normal 1

5. History Page
* Show history (ledger)

---

🎨 UI Requirements:

* Clean, modern UI (like Notion or Habit Tracker apps)
* Use cards for tasks
* Use progress indicators
* Use modal for completing tasks

---

⚙️ Tech Requirements:

* React (functional components)
* Use hooks
* Use simple state management (no Redux for now)
* Prepare for API integration

---

You can read from the models file to understand what to create first, please prepare for later UI implement

Start by:

1. Proposing folder structure
2. Designing main layout (Navbar + Pages)
3. Implement Dashboard UI first
