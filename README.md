# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started



### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:
#My example first draft:
Owner: Cristina
  Pet: Bella (12.5 kg)
    Task: Morning walk [daily] at 07:30
    Task: Evening feeding [daily] at 18:00
  Pet: Milo (4.2 kg)
    Task: Litter box change [weekly] at 12:15


```Ideal output:
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+
My tests include verifying tasks for today are shown in chronological order, testing back-to-back scheduling works, testing whether a warning is given if a duration of a previous task overlaps with a new one. As well as testing that one off tasks are allowed besides (daily, weekly) tasks.

My confidence level is 3 out of 5 stars regarding system reliability. I noted trade offs that AI warned about what is out of scope for the system like midnight scheduling overlapping between a previous and next day (not showing up on next day). I believe it addresses basic needs and functionality.
```bash
# Run the full test suite:
pytest
================================================================= 25 passed in 0.21s =================================================================
# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here

(.venv) PS C:\Users\crist\OneDrive\AI Course 2026\ai110-module2show-pawpal> python -m pytest
================================================================ test session starts =================================================================
platform win32 -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\crist\OneDrive\AI Course 2026\ai110-module2show-pawpal
collected 25 items                                                                                                                                    

tests\test_pawpal.py .........................                                                                                                  [100%]

================================================================= 25 passed in 0.10s =================================================================


```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting |_all_occurrences(),sort_by_time(), sort_by_datetime() | e.g., by each task's specific schedule (date, time). Might clash with regard to duration |
| Filtering | filter_by_pet(), filter_by_status() | Filter by pet, or task completion status. Does not yet skip tasks if time runs out |
| Conflict handling |detect_conflicts() | Overlapping time slots |
| Recurring tasks | _extend_task(), generate_occurrences() | daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
