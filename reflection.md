# PawPal+ Project Reflection

## 1. System Design

Three core actions:
1) Add a pet
2) Create future tasks
3) Edit or delete current tasks

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
<br>My initial UML design included the Owner, Pet, and Task class. Each class included the name, as well as more specialized info such as pets (for the owner class), species (for the pet class), and priority (for the task class).

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
<br>Yes. I originally only included the Owner, Pet, and Task classes. After brainstorming with the AI, I realized I had to add more classes and info to fully encapsulate the capabilities of the app. One class that I added was "Medication."

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
<br>Some constraints considered were time, priority, and conflicts. 
- How did you decide which constraints mattered most?
<br>I decided by determining which constraints would be most likely to be used and impact the user experience.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?
<br>One tradeoff my scheduler makes is the inability to edit a schedule once it has been made. This trade-off is reasonable in this scenario because another one can be made easily with the desired edits to the tasks outside of the schedule. 

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?
<br>I used AI for help in designing the UML diagram, brainstorming the features of the app, and implementing the logic and UI. I found it helpful to be specific in your instructions and have a clear idea what you want to do - if I didn't have an idea, I would ask the AI for suggestions. 

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?
<br> There was one instance where it attempted to write code into the wrong file. I changed this by clarifying the correct place the code should be written. 

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?
<br>I tested for task conflict handling, sorting, and filtering. These tests are important because it ensures that the app works as intended.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?
<br>I am about 4/5 confident it works correctly. Some edge cases I would test next if I had more time is testing with a lot of pets (>20). 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
<br>I am most satisfied with the complexity of the app in terms of sorting and creating schedules. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
<br>I would definitely spend more time improving the UI. 

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
<br>One thing I learned is that it's important to be specific and actively involved in what the AI generates. It's easy to be lead astray if you don't understand what it's generating. 
