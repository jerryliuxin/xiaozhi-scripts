"""英语Quiz系统 — 听说读写四维考察

设计原则：
1. 难度基于米奇当前积分自动分级，但题目难度对应 Cambridge B1 (Unlock Level 3)
2. 听说读写四维均衡覆盖，不是单一选择题
3. 口语/写作通过小智语音交互完成，不需要标准答案
4. 阅读/词汇/语法适合五年级认知水平(10-11岁)
5. 每次 Quiz 随机从不同维度抽取，保证多样性

难度等级（基于积分自动切换，但全部是B1水平）：
- Level 1 (0-200分): 基础B1 — 简单对话、看图说话、基础词汇
- Level 2 (200-500分): 进阶B1 — 段落阅读、复杂句型、情景对话
- Level 3 (500+分): 高阶B1 — 议论文阅读、长对话、学术词汇

技能维度：
- 听力: 描述一个场景/故事，米奇听完后回答
- 口语: 给米奇一个话题/图片描述任务，用语音回答
- 阅读: 短文阅读+理解题（不是GRE，是适合孩子的短文）
- 词汇: 语境中猜词义、近义词、搭配
- 语法: 填空、改错、句型转换
- 写作: 一句话造句、看图写话（语音输出）
"""

import random
from datetime import date

# ============================================================
# Level 1: 基础B1 (0-200分) — 适合刚开始学
# ============================================================

LEVEL_1 = {
    # --- 听力理解 ---
    "listening": [
        {
            "type": "listening",
            "text": "Imagine: It's a sunny Saturday morning. You are in the park with your dog. There are three children playing football near the trees. Two birds are sitting on a bench. What do you hear?",
            "question": "What day is it? What is the weather like? How many children are playing?",
            "answer": "Saturday, sunny, 3 children",
            "explain": "This tests listening for specific details — day, weather, and number.",
        },
        {
            "type": "listening",
            "text": "Listen carefully: 'My name is Amy. I'm eleven years old. I live in Beijing. My favorite subject is science because I like doing experiments.'",
            "question": "How old is Amy? What is her favorite subject? Why?",
            "answer": "11 years old, science, likes experiments",
            "explain": "Listening for personal information and reasons.",
        },
        {
            "type": "listening",
            "text": "Listen: 'The library opens at 9:00 a.m. and closes at 5:00 p.m. on weekdays. On weekends, it's open from 10:00 a.m. to 4:00 p.m.'",
            "question": "What time does the library close on weekdays? What about weekends?",
            "answer": "Weekdays: 5pm, Weekends: 4pm",
            "explain": "Listening for times and schedules.",
        },
    ],
    
    # --- 口语表达 ---
    "speaking": [
        {
            "type": "speaking",
            "prompt": "Describe your favorite food. What is it? Why do you like it? When do you usually eat it?",
            "evaluation": "Looks for: food name, reason (because...), time (usually/often), full sentences",
            "example_answer": "My favorite food is dumplings. I like them because they are delicious and my mom makes them on weekends. We usually eat them during Chinese New Year.",
        },
        {
            "type": "speaking",
            "prompt": "Tell me about your best friend. What is his/her name? What do you like to do together?",
            "evaluation": "Looks for: name, hobbies together, descriptive adjectives",
            "example_answer": "My best friend is Tom. He is tall and funny. We like playing basketball and video games together after school.",
        },
        {
            "type": "speaking",
            "prompt": "What did you do last weekend? Tell me 3 things.",
            "evaluation": "Looks for: past tense (went, played, watched, visited), 3 events, time expressions",
            "example_answer": "Last weekend, I visited my grandparents on Saturday. I played football with my friend on Sunday morning. On Sunday afternoon, I read a book.",
        },
        {
            "type": "speaking",
            "prompt": "Describe what you can see in this picture: a beach scene with palm trees, the ocean, and children building a sandcastle.",
            "evaluation": "Looks for: spatial words (there is/are, near, next to), descriptive adjectives, present continuous",
            "example_answer": "There is a beautiful beach. There are tall palm trees near the ocean. Some children are building a big sandcastle. The water is blue and clear.",
        },
    ],
    
    # --- 阅读理解 ---
    "reading": [
        {
            "type": "reading",
            "text": "Tom is a 12-year-old boy from London. He loves sports. Every morning, he runs for 30 minutes before school. On Mondays and Wednesdays, he plays football with his classmates. On Fridays, he goes swimming with his dad. Tom's dream is to play football for England one day.",
            "questions": [
                {"q": "How old is Tom?", "a": "12 years old", "explain": "Direct detail from the first sentence."},
                {"q": "What does Tom do every morning?", "a": "Runs for 30 minutes", "explain": "'Every morning, he runs for 30 minutes'"},
                {"q": "Where does Tom live?", "a": "London", "explain": "First sentence: 'from London'"},
                {"q": "What is Tom's dream?", "a": "To play football for England", "explain": "Last sentence directly states his dream."},
            ],
        },
        {
            "type": "reading",
            "text": "The honeybee is one of the most important insects. Bees fly from flower to flower, collecting nectar. While doing this, they carry pollen on their legs. This helps new plants grow. A single hive can have up to 60,000 bees. The queen bee lays up to 2,000 eggs every day!",
            "questions": [
                {"q": "Why are bees important?", "a": "They help new plants grow by carrying pollen", "explain": "Bees carry pollen from flower to flower."},
                {"q": "What do bees collect from flowers?", "a": "Nectar", "explain": "Directly stated in the text."},
                {"q": "How many bees can be in one hive?", "a": "Up to 60,000", "explain": "'up to 60,000 bees'"},
            ],
        },
        {
            "type": "reading",
            "text": "In Japan, there is a special train called the Shinkansen, or 'bullet train.' It can travel at 320 kilometers per hour! The first Shinkansen started in 1964, before the Internet was invented. Trains in Japan are so on time that if a train is only one minute late, the conductor must apologize to the passengers.",
            "questions": [
                {"q": "What is the Shinkansen?", "a": "A Japanese bullet train", "explain": "First sentence explains it clearly."},
                {"q": "How fast can it go?", "a": "320 km/h", "explain": "'320 kilometers per hour'"},
                {"q": "What happens if a train is late?", "a": "The conductor apologizes", "explain": "Last sentence explains this Japanese tradition."},
            ],
        },
    ],
    
    # --- 词汇 ---
    "vocabulary": [
        {
            "type": "vocabulary",
            "question": "In the sentence 'She was very ________ after running for 20 minutes,' which word fits best? A) hungry B) tired C) beautiful D) quickly",
            "a": "B",
            "explain": "'Tired' makes sense after physical exercise. 'Hungry' could also work, but 'tired' is the most natural choice after running.",
        },
        {
            "type": "vocabulary",
            "question": "What does 'discover' mean? A) to lose something B) to find something for the first time C) to destroy D) to hide",
            "a": "B",
            "explain": "'Discover' means to find something new — like Columbus discovering America (though people already lived there!).",
        },
        {
            "type": "vocabulary",
            "question": "Choose the correct word: 'The book is ________ the table.' A) on B) at C) in the D) to",
            "a": "A",
            "explain": "'On' is used for surfaces. The book rests ON the surface of the table.",
        },
        {
            "type": "vocabulary",
            "question": "'Helpful' is closest in meaning to: A) lazy B) willing to help C) angry D) clever",
            "a": "B",
            "explain": "'Helpful' means willing to give help — a helpful person helps others.",
        },
        {
            "type": "vocabulary",
            "question": "Which word is the opposite of 'expensive'? A) beautiful B) cheap C) large D) heavy",
            "a": "B",
            "explain": "'Cheap' means not expensive — the opposite.",
        },
    ],
    
    # --- 语法 ---
    "grammar": [
        {
            "type": "grammar",
            "question": "Fill in the blank: 'Mickey ______ (go) to school every day.' A) go B) goes C) going D) gone",
            "a": "B",
            "explain": "Third person singular (he/Mickey) + present simple = 'goes'. Every day = habitual action, so present simple.",
        },
        {
            "type": "grammar",
            "question": "Choose the correct sentence: A) She don't like apples. B) She doesn't likes apples. C) She doesn't like apples. D) She not like apples.",
            "a": "C",
            "explain": "Third person negative: doesn't + base verb. 'She doesn't like' is correct.",
        },
        {
            "type": "grammar",
            "question": "Fill in the blank: 'Yesterday, I ______ a wonderful movie.' A) watch B) watches C) watched D) watching",
            "a": "C",
            "explain": "'Yesterday' = past tense. 'Watched' is the past simple of 'watch'.",
        },
        {
            "type": "grammar",
            "question": "Which is correct? A) There is many books. B) There are many books. C) There have many books. D) There has many books.",
            "a": "B",
            "explain": "'There are' + plural noun. Books = plural, so 'there are'.",
        },
    ],
    
    # --- 写作 ---
    "writing": [
        {
            "type": "writing",
            "prompt": "Write one sentence using the word 'because'.",
            "example": "I like summer because I can swim in the pool.",
            "evaluation": "Must use 'because' correctly to show a reason.",
        },
        {
            "type": "writing",
            "prompt": "Write two sentences about your favorite season. Use 'because' in one of them.",
            "example": "My favorite season is autumn. The weather is cool and the leaves turn beautiful colors.",
            "evaluation": "Two sentences, uses 'because' correctly, describes a season.",
        },
        {
            "type": "writing",
            "prompt": "Imagine you find a magic key. Write two sentences about what you would do.",
            "example": "I would use the magic key to open a door to another world. I would bring my best friend with me!",
            "evaluation": "Uses 'would' for imaginary situations, shows creativity.",
        },
    ],
}


# ============================================================
# Level 2: 进阶B1 (200-500分) — 有一定基础
# ============================================================

LEVEL_2 = {
    "listening": [
        {
            "type": "listening",
            "text": "Listen carefully: 'Last summer, my family and I went on a trip to the mountains. We stayed in a small cabin near a river. Every morning, I woke up to the sound of birds singing. One afternoon, we saw a deer drinking water at the riverbank. It was the most peaceful moment I've ever experienced.'",
            "question": "Where did they go? What did they stay in? What did Mickey see at the river?",
            "answer": "Mountains, a cabin near a river, a deer",
            "explain": "Listening for a sequence of events and details.",
        },
        {
            "type": "listening",
            "text": "Listen: 'In many countries, people celebrate New Year's Day in different ways. In Spain, they eat 12 grapes at midnight — one for each month. In Japan, they ring a temple bell 108 times to cleanse bad habits. In Brazil, people wear white clothes to bring good luck for the new year.'",
            "question": "What do people do in each country for New Year?",
            "answer": "Spain: 12 grapes, Japan: 108 bell rings, Brazil: wear white",
            "explain": "Listening for comparisons and cultural facts.",
        },
    ],
    
    "speaking": [
        {
            "type": "speaking",
            "prompt": "If you could invent something to help people, what would it be? Explain why it would be useful. Use: 'I would invent... because...'",
            "evaluation": "Uses 'would' for hypothetical, explains purpose, shows reasoning",
            "example_answer": "I would invent a robot that helps elderly people. Because some old people live alone and need help with daily tasks like cooking and cleaning.",
        },
        {
            "type": "speaking",
            "prompt": "Discuss: Is it better to live in a city or in the countryside? Give two reasons for your opinion.",
            "evaluation": "Expresses opinion, gives 2 reasons, uses connecting words (because, also, however)",
            "example_answer": "I think living in the city is better. First, there are more schools and hospitals. Second, you can find more interesting things to do.",
        },
        {
            "type": "speaking",
            "prompt": "Tell a short story about something surprising that happened to you. Use: first, then, after that, finally.",
            "evaluation": "Uses sequencing words, past tense narrative, complete story arc",
            "example_answer": "First, I went to the park. Then, I saw a lost puppy. After that, I looked for its owner near the gate. Finally, a little girl came running — it was her dog!",
        },
    ],
    
    "reading": [
        {
            "type": "reading",
            "text": "The Great Wall of China is the longest wall ever built. It stretches over 21,000 kilometers — that's like going from the North Pole to the South Pole and back again! The wall was not built all at once. Different dynasties built sections over hundreds of years. The oldest parts are more than 2,000 years old. People built the wall to protect China from invasions. It took millions of workers over many centuries. Today, it is one of the most visited sites in the world.",
            "questions": [
                {"q": "How long is the Great Wall?", "a": "Over 21,000 kilometers", "explain": "Directly stated: 'over 21,000 kilometers'"},
                {"q": "Was it built all at once?", "a": "No, different dynasties built it over hundreds of years", "explain": "'Different dynasties built sections over hundreds of years'"},
                {"q": "Why was it built?", "a": "To protect China from invasions", "explain": "'built the wall to protect China from invasions'"},
                {"q": "How old are the oldest parts?", "a": "More than 2,000 years", "explain": "'The oldest parts are more than 2,000 years old'"},
            ],
        },
        {
            "type": "reading",
            "text": "Sleep is very important for students. During sleep, your brain organizes everything you learned that day. Scientists say teenagers need 8-10 hours of sleep each night. But many students only get 6 hours. This can cause problems: difficulty concentrating in class, forgetfulness, and even feeling sad. Experts suggest keeping a regular sleep schedule, avoiding screens one hour before bed, and keeping the bedroom cool and dark.",
            "questions": [
                {"q": "Why is sleep important for the brain?", "a": "It organizes everything learned that day", "explain": "'During sleep, your brain organizes everything you learned'"},
                {"q": "How much sleep do teenagers need?", "a": "8-10 hours", "explain": "'teenagers need 8-10 hours of sleep each night'"},
                {"q": "What problems can lack of sleep cause?", "a": "Difficulty concentrating, forgetfulness, feeling sad", "explain": "Three problems listed in the text"},
                {"q": "What does 'experts' recommend?", "a": "Regular schedule, no screens before bed, cool/dark room", "explain": "Last sentence lists three suggestions"},
            ],
        },
    ],
    
    "vocabulary": [
        {
            "type": "vocabulary",
            "question": "In the sentence 'The movie was so boring that I almost fell asleep,' what does 'boring' describe? A) The audience B) The movie C) The theater D) The popcorn",
            "a": "B",
            "explain": "'Boring' describes the movie — the thing that causes boredom.",
        },
        {
            "type": "vocabulary",
            "question": "What does 'environment' mean? A) a large house B) the natural world around us C) a type of vehicle D) a computer game",
            "a": "B",
            "explain": "'Environment' = the natural world including air, water, land, plants, and animals.",
        },
        {
            "type": "vocabulary",
            "question": "Choose the correct word: 'We should _______ our environment by recycling and saving water.' A) protect B) product C) project D) produce",
            "a": "A",
            "explain": "'Protect' means to keep safe — protecting the environment.",
        },
        {
            "type": "vocabulary",
            "question": "'Success' is a noun. What is the adjective form? A) succeed B) successful C) successfully D) succeedful",
            "a": "B",
            "explain": "'Successful' is the adjective. 'He is a successful student.'",
        },
    ],
    
    "grammar": [
        {
            "type": "grammar",
            "question": "Choose the correct sentence: A) I have been to London last year. B) I went to London last year. C) I go to London last year. D) I going to London last year.",
            "a": "B",
            "explain": "'Last year' = specific past time = past simple. 'Went' is past simple of 'go'.",
        },
        {
            "type": "grammar",
            "question": "Fill in the blank with the correct form: 'If I _______ rich, I would travel around the world.' A) am B) was C) were D) be",
            "a": "C",
            "explain": "This is a hypothetical situation (Type 2 conditional). Use 'were' for all subjects in hypothetical 'if' clauses.",
        },
        {
            "type": "grammar",
            "question": "Choose the correct passive sentence: A) The book wrote by Lu Xun. B) The book was written by Lu Xun. C) The book is write by Lu Xun. D) The book written by Lu Xun.",
            "a": "B",
            "explain": "Past passive: was/were + past participle. 'was written'.",
        },
        {
            "type": "grammar",
            "question": "Which sentence uses a relative clause correctly? A) The girl which is wearing a red dress is my sister. B) The girl who is wearing a red dress is my sister. C) The girl whom is wearing a red dress is my sister.",
            "a": "B",
            "explain": "'Who' is used for people as the subject of a relative clause. 'Which' is for things.",
        },
    ],
    
    "writing": [
        {
            "type": "writing",
            "prompt": "Write a paragraph (3-4 sentences) explaining why it's important to learn English. Use: first, second, finally.",
            "example": "First, English is a useful skill for finding a good job. Second, it helps you understand movies and music without translation. Finally, learning English allows you to make friends from other countries.",
            "evaluation": "Uses sequencing words, gives reasons, complete paragraph structure",
        },
        {
            "type": "writing",
            "prompt": "Write about your dream job. What would you do? Why? Use: 'I would like to... because...' and 'This is because...'",
            "example": "I would like to be a scientist because I love discovering new things. This is because science helps us understand how the world works.",
            "evaluation": "Expresses aspiration, gives reasons, uses required phrases",
        },
    ],
}


# ============================================================
# Level 3: 高阶B1 (500+分) — 接近B1上限
# ============================================================

LEVEL_3 = {
    "listening": [
        {
            "type": "listening",
            "text": "Listen carefully: 'A recent study found that students who take regular breaks while studying perform better than those who study for long periods without rest. The researchers suggest the 'Pomodoro Technique': study for 25 minutes, then take a 5-minute break. After four breaks, take a longer 15-30 minute break. This method helps the brain process information more effectively.'",
            "question": "What did the study find? What is the Pomodoro Technique? What are the break intervals?",
            "answer": "Regular breaks improve performance; 25 min study + 5 min break, after 4 cycles take 15-30 min break",
            "explain": "Listening for specific information: findings, method, numbers.",
        },
        {
            "type": "listening",
            "text": "Listen: 'The Amazon rainforest is often called the 'lungs of the Earth' because it produces about 20% of the world's oxygen. However, deforestation is destroying about 27 football fields of forest every minute. Scientists estimate that if we continue at this rate, we could lose 17% of the Amazon by 2030. This would affect not only the many animals that live there, but also the global climate.'",
            "question": "Why is it called the lungs of the Earth? What is happening to it? What could happen by 2030?",
            "answer": "Produces 20% of world's oxygen; being destroyed at 27 football fields/minute; 17% could be lost by 2030",
            "explain": "Listening for facts, numbers, consequences.",
        },
    ],
    
    "speaking": [
        {
            "type": "speaking",
            "prompt": "Debate topic: Should students use smartphones in school? Give your opinion and two strong arguments. Then try to think of one counter-argument.",
            "evaluation": "Clear opinion, 2 arguments, acknowledges counter-argument, uses linking words",
            "example_answer": "I think students shouldn't use smartphones in school. First, they distract from learning. Second, students might cheat during tests. However, some people say phones can help with research — which is true, but schools have computers for that.",
        },
        {
            "type": "speaking",
            "prompt": "Describe a book or movie that changed your perspective on something. What was the main idea? How did it affect you?",
            "evaluation": "Narrative + reflection, past + present tenses, abstract thinking",
            "example_answer": "The movie 'WALL-E' changed how I think about technology. It shows a world where humans have become lazy and dependent on machines. It made me realize that we should not rely too much on devices.",
        },
    ],
    
    "reading": [
        {
            "type": "reading",
            "text": "Artificial Intelligence (AI) is transforming many aspects of our daily lives. From voice assistants like Siri and Alexa to recommendation systems on Netflix, AI is everywhere. In healthcare, AI algorithms can analyze medical images faster than human doctors and sometimes more accurately. In education, AI-powered tutors can provide personalized learning for each student. However, there are concerns about AI: privacy, job displacement, and the risk of over-reliance. Experts agree that we need regulations to ensure AI is developed responsibly and benefits everyone.",
            "questions": [
                {"q": "What are two examples of AI in daily life mentioned?", "a": "Voice assistants (Siri/Alexa) and recommendation systems (Netflix)", "explain": "First sentence gives two clear examples"},
                {"q": "How is AI used in healthcare?", "a": "Analyzing medical images faster and sometimes more accurately than doctors", "explain": "'AI algorithms can analyze medical images faster than human doctors'"},
                {"q": "What are the concerns about AI mentioned?", "a": "Privacy, job displacement, over-reliance", "explain": "Three concerns listed in the text"},
                {"q": "What do experts agree on?", "a": "We need regulations for responsible AI development", "explain": "'Experts agree that we need regulations'"},
            ],
        },
        {
            "type": "reading",
            "text": "The concept of 'green cities' is becoming increasingly popular. A green city uses renewable energy, has extensive public transport, and includes many parks and gardens. Copenhagen, Denmark, is often considered the world's greenest city. Over 60% of its residents cycle to work or school every day. The city has invested heavily in wind power and aims to become carbon-neutral by 2025. Other cities like Singapore and Vancouver are also leading the way with innovative sustainability projects.",
            "questions": [
                {"q": "What makes a city 'green'?", "a": "Renewable energy, public transport, parks/gardens", "explain": "Second sentence lists three characteristics"},
                {"q": "Which city is considered the greenest?", "a": "Copenhagen, Denmark", "explain": "'Copenhagen... is often considered the world's greenest city'"},
                {"q": "How many Copenhagen residents cycle to work/school?", "a": "Over 60%", "explain": "'Over 60% of its residents cycle'"},
                {"q": "When does Copenhagen aim to be carbon-neutral?", "a": "2025", "explain": "'aims to become carbon-neutral by 2025'"},
            ],
        },
    ],
    
    "vocabulary": [
        {
            "type": "vocabulary",
            "question": "What does 'sustainable' mean in the sentence 'We need sustainable energy sources'? A) energy from the sun B) energy that can continue for a long time without running out C) very expensive energy D) energy from coal",
            "a": "B",
            "explain": "'Sustainable' means able to continue without being used up completely.",
        },
        {
            "type": "vocabulary",
            "question": "Choose the correct word: 'The government needs to _______ new laws to protect the environment.' A) legislation B) legislative C) legislate D) legislator",
            "a": "C",
            "explain": "Need a verb after 'to'. 'Legislate' is the verb meaning 'to make laws'.",
        },
        {
            "type": "vocabulary",
            "question": "'Innovation' is related to: A) following traditions B) creating new ideas and methods C) copying others D) stopping progress",
            "a": "B",
            "explain": "'Innovation' = the introduction of new ideas, methods, or things.",
        },
    ],
    
    "grammar": [
        {
            "type": "grammar",
            "question": "Choose the correct sentence with a present perfect tense: A) I have visited the museum yesterday. B) I have visited the museum many times. C) I visiting the museum last week. D) I visit the museum since 2020.",
            "a": "B",
            "explain": "Present perfect (have/has + past participle) is used for experiences without a specific time. 'Yesterday' cannot be used with present perfect.",
        },
        {
            "type": "grammar",
            "question": "Fill in the blank: 'By the time we arrived, the movie _______.' A) already started B) had already started C) has already started D) was already starting",
            "a": "B",
            "explain": "Past perfect (had + past participle) is used when one past action happened before another past action.",
        },
        {
            "type": "grammar",
            "question": "Combine these sentences: 'The boy is standing there. He is wearing a blue shirt.' → ",
            "a": "The boy who is wearing a blue shirt is standing there.",
            "explain": "Combine using a relative clause: 'who' refers to the boy, 'wearing a blue shirt' describes him.",
        },
    ],
    
    "writing": [
        {
            "type": "writing",
            "prompt": "Write a short opinion paragraph (4-5 sentences): 'Social media has more advantages than disadvantages for teenagers.' Do you agree or disagree? Give two reasons.",
            "example": "I disagree that social media has more advantages. First, it can cause addiction and waste time. Second, cyberbullying is a serious problem that affects many teenagers. However, it can help people stay connected with friends.",
            "evaluation": "Clear position, 2 reasons, acknowledges counterpoint, paragraph structure",
        },
        {
            "type": "writing",
            "prompt": "Imagine you are writing a letter to your future self (10 years from now). Write 3-4 sentences about what you hope your life will be like.",
            "example": "Dear Future Me, I hope you have become a successful scientist and published many important papers. I hope you still play football every weekend and have kept in touch with your old friends. I hope you haven't lost your sense of humor!",
            "evaluation": "Uses future tense (will/hope), personal tone, specific goals",
        },
    ],
}


# ============================================================
# 难度选择器
# ============================================================

def get_quiz(difficulty=None, total_score=None):
    """
    根据积分获取英语Quiz内容。
    
    difficulty: 手动指定难度（"level1"/"level2"/"level3"）
    total_score: 当前总积分（自动判定难度）
    
    返回：包含题目类型、内容、正确答案、评分标准的字典
    """
    if total_score is None:
        import game_engine
        total_score = game_engine.get_score().get("total_score", 0)
    
    if difficulty is None:
        if total_score < 200:
            level = "level1"
        elif total_score < 500:
            level = "level2"
        else:
            level = "level3"
    elif difficulty == "level1":
        level = "level1"
    elif difficulty == "level2":
        level = "level2"
    else:
        level = "level3"
    
    pools = {
        "level1": LEVEL_1,
        "level2": LEVEL_2,
        "level3": LEVEL_3,
    }
    pool = pools[level]
    
    # 从所有维度随机选择一个
    skills = list(pool.keys())  # listening, speaking, reading, vocabulary, grammar, writing
    skill_type = random.choice(skills)
    items = pool[skill_type]
    item = random.choice(items)
    
    # 添加难度标签
    level_labels = {
        "level1": "基础B1 (Level 1)",
        "level2": "进阶B1 (Level 2)",
        "level3": "高阶B1 (Level 3)",
    }
    skill_labels = {
        "listening": "👂 听力理解",
        "speaking": "🗣️ 口语表达",
        "reading": "📖 阅读理解",
        "vocabulary": "📝 词汇",
        "grammar": "📐 语法",
        "writing": "✍️ 写作",
    }
    
    result = {
        "skill_type": skill_type,
        "skill_label": skill_labels[skill_type],
        "difficulty": level,
        "difficulty_label": level_labels[level],
        "item": item,
    }
    
    return result


def get_quiz_prompt(difficulty=None, total_score=None):
    """生成英语Quiz的完整Prompt，供小智调用。"""
    quiz = get_quiz(difficulty, total_score)
    skill_type = quiz["skill_type"]
    item = quiz["item"]
    
    score_info = None
    try:
        import game_engine
        score_info = game_engine.get_score()
    except Exception:
        pass
    
    score_text = ""
    if score_info:
        score_text = f"📊 当前积分: {score_info['total_score']} | 等级: {score_info['level']}\n"
    
    # 只生成当前技能类型的Prompt
    if skill_type == "listening":
        prompt = generate_listening_prompt(item, quiz, score_text)
    elif skill_type == "speaking":
        prompt = generate_speaking_prompt(item, quiz, score_text)
    elif skill_type == "reading":
        prompt = generate_reading_prompt(item, quiz, score_text)
    elif skill_type == "vocabulary":
        prompt = generate_vocabulary_prompt(item, quiz, score_text)
    elif skill_type == "grammar":
        prompt = generate_grammar_prompt(item, quiz, score_text)
    elif skill_type == "writing":
        prompt = generate_writing_prompt(item, quiz, score_text)
    else:
        prompt = generate_vocabulary_prompt(item, quiz, score_text)
    return prompt


def generate_listening_prompt(item, quiz_info, score_text):
    return f"""【👂 听力理解训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日听力任务：

听力材料：
{item['text']}

问题：
{item['question']}

参考答案：
{item['answer']}

📋 解析：
{item['explain']}

执行步骤：
1. 用清晰、稍慢的语速朗读听力材料（英文）
2. 读完后用中文解释题目要求
3. 给米奇思考时间，然后提问
4. 引导米奇用完整句子回答
5. 回答正确后展示参考答案和解析
6. 鼓励米奇："你听力很棒！+15分！"

注意：不要直接给答案，要引导米奇自己回答！
"""

def generate_speaking_prompt(item, quiz_info, score_text):
    return f"""【🗣️ 口语表达训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日口语任务：

话题/任务：
{item.get('prompt', item.get('question', ''))}

评价标准：
{item.get('evaluation', '')}

参考答案示例：
{item.get('example_answer', item.get('answer', ''))}

执行步骤：
1. 用中文介绍今天的口语任务
2. 给出提示和鼓励
3. 等米奇用语音回答（语音转文字后评估）
4. 评估标准：
   - 内容：是否完整回答了问题
   - 语法：是否有明显语法错误
   - 词汇：是否使用了合适的词汇
   - 流利度：表达是否流畅
5. 给出积极反馈和评分
6. 说："口语练习完成！+15分！"

注意：口语题没有标准答案，重点在鼓励表达！
"""

def generate_reading_prompt(item, quiz_info, score_text):
    questions_text = ""
    for i, q in enumerate(item['questions'], 1):
        questions_text += f"{i}. Q: {q['q']}\n   A: {q['a']}\n   解析: {q['explain']}\n\n"
    
    return f"""【📖 阅读理解训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日阅读任务：
阅读材料：
{item['text']}

理解问题：
{questions_text}

执行步骤：
1. 用稍慢的语速朗读阅读材料（英文），读两遍
2. 用中文解释材料大意，帮助理解
3. 逐题提问，给米奇思考时间
4. 每答完一题，解释答案为什么正确
5. 全部完成后总结："阅读理解完成！答对了X题，+15分！"

注意：阅读材料是适合五年级B1水平的科普/故事类文章！
"""

def generate_vocabulary_prompt(item, quiz_info, score_text):
    return f"""【📝 词汇训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日词汇任务：

题目：
{item['question']}

正确答案：{item['a']}
解析：{item['explain']}

执行步骤：
1. 用中文介绍今天的词汇任务
2. 先引导米奇理解句子/词语的意思
3. 让米奇先猜答案，再给出选项
4. 选对后解释为什么
5. 选错后温柔解释正确答案
6. 说："词汇闯关成功！+15分！"

注意：每道题要解释清楚词汇在语境中的意思！
"""

def generate_grammar_prompt(item, quiz_info, score_text):
    return f"""【📐 语法训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日语法任务：

题目：
{item['question']}

正确答案：{item['a']}
解析：{item['explain']}

执行步骤：
1. 用中文介绍语法点（先讲规则，再做题）
2. 让米奇先思考规则
3. 给出题目和选项
4. 选对/选错后都解释语法规则
5. 说："语法闯关成功！+15分！"

注意：每道题都要讲清楚语法规则，不只是给答案！
"""

def generate_writing_prompt(item, quiz_info, score_text):
    return f"""【✍️ 写作训练】
{quiz_info['difficulty_label']} | {quiz_info['skill_label']}

{score_text}🎯 今日写作任务：

题目：
{item['prompt']}

参考答案示例：
{item['example']}

评价标准：
{item['evaluation']}

执行步骤：
1. 用中文解释写作任务，鼓励米奇动笔（或语音说出一句话）
2. 引导米奇写出完整的句子
3. 评估：
   - 语法是否正确
   - 是否有拼写错误
   - 是否完整回答了问题
   - 创意和多样性
4. 给出积极反馈
5. 说："写作完成！+15分！"

注意：写作题鼓励用语音输出一句话，不要求长篇大论！
"""


if __name__ == "__main__":
    print("=== 英语Quiz系统测试 ===")
    
    for level in ["level1", "level2", "level3"]:
        print(f"\n=== {level} ===")
        for _ in range(3):
            quiz = get_quiz(level)
            print(f"  {quiz['skill_label']}: {quiz['item']['type']}")
    
    # 测试自动难度选择
    print("\n=== 自动难度选择 ===")
    for score in [50, 150, 300, 600, 1000]:
        quiz = get_quiz(total_score=score)
        print(f"  积分 {score}: {quiz['difficulty_label']}")
    
    print("\n=== Prompt生成测试 ===")
    prompt = get_quiz_prompt(total_score=100)
    print(f"  Prompt长度: {len(prompt)} chars")
    print(f"  前200字: {prompt[:200]}...")
