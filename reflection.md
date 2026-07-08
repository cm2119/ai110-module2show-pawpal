# PawPal+ Project Reflection

## 1. System Design
/Additional Notes/
Core User Actions
1. Writing down pet name/info
2. See a summary of today's tasks with logic that priotized given tasks
3. Add tasks + schedule tasks

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
Attributes (info to hold) vs Methods (actions it can perform)
Owner: user information
    -Attributes: Name, information about their pet(s)
    -Methods: Add a pet
Pets: stores individual pet information like name, weight (user can have multiple pets)
    NOTE: 'Owner has Pets'
    -Attributes: Name, Weight
    -Methods: edit pet information
Tasks: stores all tasks created by user/owner like walking, feeding
    -Attributes: Tasks designated to a particular pet
    -Methods: Add a task for a pet
Schedule: stores particular time in a day where a task must be performed
    -Attributes: Task for a particular pet
    -Methods: Add a specific time for said task for a pet to be performed in a day


**b. Design changes**

- Did your design change during implementation?
Yes.
- If yes, describe at least one change and why you made it.
I had to edit the placement of certain responsibilities and remove extra functions that had the same purpose. For instance, I adjusted how tasks would handle the time they are supposed to be performed to be in a different class "Schedule" that is in charge of when a task must be done and that it handles if a task must be done more than once a day like feeding. 
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
My scheduler considers date and time for each task by detecting conflicts if tasks overlap in date and time. It prioritzes tasks by time if given. 
- How did you decide which constraints mattered most?
I noticed my code 

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
For task conflict detection, I made a tradeoff by swapping from three overlapping ideas to a single grouping logic to improve human readibility that allows for identifying whether tasks have the same date and time to produce a warning. This warning considers printing a single readable warning line instead of multiple for each time there is a conflict.

- Why is that tradeoff reasonable for this scenario?
It is reasonable because I didn't follow through in a reasonable manner with the initial overlapping ideas for sorting provided by AI. So, this refactoring was helpful because I felt more confident about the code and for anyone else to follow through by prioritizing readibility and even acknowledging that the logic relies on sorting by date and time first before identifying tasks that conflict with each other.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
