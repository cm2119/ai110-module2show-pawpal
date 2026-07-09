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
I was astonished at how AI was quite incredibibly helpful for understanding goals before jumping into code, explaining complex code, debugging previously generated code with my observations as I ran the app, and refactoring overly complex code. For instance, if I wasn't careful with its suggestions I would force it to analyze a specific function in a new tab where it realizes logic mistakes, that is, when it combined too many solutions while a simpler one would make more and be more code reader friendly.

- What kinds of prompts or questions were most helpful?
I noticed the most helpful prompts were the ones where I sough to focus in a specific goal, no matter how small, so I could stay in pace with increasingly long and very advanced functions. However, I sometimes asked for its help in dividing tasks and then inquired to focus on each one at once which helped making things slightly less overwhelming.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
Since it felt very stressful to not be able to understand completely every function implementation (although AI helped explain what code snippets did and the main goal for me to comprehend before implementing suggestions), I had to defer how it suggested to add more algorithms that made the scheduler "smarter". After adding core implementation, I felt if I wasnt careful with my prompt it would try to chunk several different goals into very huge functions. So I decided to be more niche and just focus on every algorithm at a time, and then I analyzed its suggestions for further complexity like considering a task's priority, how the algorithm would place times if requested by the user, and provide explanations when it made scheduling decisions.

- How did you evaluate or verify what the AI suggested?
I definetely wanted AI to explain the goal and how it would approach a problem before I accepted code additions every time. This saved me a lot of time since I only encountered a couple errors where the UI wasn't up to date or used new back end logic innacurately. I verified what it meant to do aligned with what I wanted it to perform.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
I tested a huge lot of behaviors as I thought of or AI pointed out for potential adverse effects and with tests as I implemented every new logic. Most important tests included: making sure the suggested new schedule was in chronological order, that recurring tasks added themselves into future upcoming tasks, whether Pawpal accurately selected times if the user desired so.

- Why were these tests important?
The tests I mentioned were critical as I noticed as I tested the app myself several times. They were aspects that met the basic needs of the users and therefore should not be prone to obvious edge cases.

**b. Confidence**

- How confident are you that your scheduler works correctly?
I'm somewhat confident that my scheduler meets the desired requirements, even though I spent a lot of time working on pre-existent generated code, addressing bugs with AI, I found it necessary to be consistent and update work wherever necessary to prevent random bugs.

- What edge cases would you test next if you had more time?
I'd be interested in testing cases like how does my system behave if their duration was longer than the whole time window, a negative duration (which might reject), whether there is a limit to future task occurrences table for recurring tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
I'm quite satisfied with how I added a re-plan button because I thought it would be a helpful feature if the user decided to add more important tasks (high priority, medium) that should happen earlier or at another time and to be considered again by the scheduling algorithms.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I'd definetely work upon niche interactions like making sure the UI implements pet editing/owner info/task info (maybe editing the properties of a task) which would make the app much more immersive much like a real very functional app.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
To be fair, it still feels strange to me how AI can perform complex code that meets the desired goal insanely fast as long as the prompts keep it focused and I'm clear about what I aim for. It was also very great for organizing my ideas and explaining suggestions for me to decide how to go about with a problem. I acknowledge the code isn't fully perfect and I'd do refactoring to make sure the code is logical and human readable. Its quite a hefty task to stay on track with code syntax and what its doing without feeling a bit outperformed by AI in terms of code writing. Thankfully, AI performs best on very small tasks rather than asking it to complete an entire system of its own.