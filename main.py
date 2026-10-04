import asyncio
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import flet as ft

# ===============================================================
# FitLife - personal digital gym coach
# Everything lives in this one file, in clear sections:
#   1. Settings & colors
#   2. Workout data (programs + exercise instructions)
#   3. Saved user data (loaded from / saved to a local file)
#   4. Helper functions (dates, weights, stats)
#   5. Small reusable UI pieces
#   6. Popups (dialogs and bottom sheets)
#   7. Screens
#   8. Main app (navigation)
#   New in v0.3: first-launch onboarding (10 questions)
#   New in v0.4: 30-day plan generator (logic only, saved in fitlife_data.json)
#   New in v0.5: My 30-Day Plan screen (reads the saved plan; opened from Home)
#   New in v0.6: finishing a workout opened from the plan completes that plan day
#   New in v0.7: Home is now the 30-day coaching dashboard (journey card + today's plan)
#   New in v0.8: Fitness Plan screen (Profile > Fitness Plan)
# ===============================================================

# ---------------------------------------------------------------
# 1. SETTINGS
# ---------------------------------------------------------------
BG_COLOR = "#0F1115"        # main background (almost black)
CARD_COLOR = "#1A1D24"      # card background
CARD_LIGHT = "#242833"      # slightly lighter boxes inside cards
ACCENT = "#B6FF3B"          # neon lime accent color
TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#8A90A0"
DANGER = "#FF5C5C"

KG_TO_LB = 2.20462


# ---------------------------------------------------------------
# 2. WORKOUT DATA
# ---------------------------------------------------------------
def exercise(name, muscle, sets, reps, rest):
    """Small helper that builds one exercise entry (keeps the data tidy)."""
    return {"name": name, "muscle": muscle, "sets": sets, "reps": reps, "rest": rest}


# All workout programs. Each one has a list of exercises.
WORKOUTS = [
    {
        "name": "Full Body",
        "description": "Train every major muscle group",
        "duration": "35 min",
        "level": "Beginner",
        "icon": ft.Icons.ACCESSIBILITY_NEW,
        "exercises": [
            exercise("Bodyweight Squats", "Legs", 3, "12 reps", 60),
            exercise("Push-Ups", "Chest", 3, "10 reps", 60),
            exercise("Dumbbell Rows", "Back", 3, "12 reps", 60),
            exercise("Shoulder Press", "Shoulders", 3, "10 reps", 60),
            exercise("Lunges", "Legs", 3, "12 reps", 60),
            exercise("Plank", "Core", 3, "30 sec", 45),
        ],
    },
    {
        "name": "Push Day",
        "description": "Chest, shoulders and triceps",
        "duration": "40 min",
        "level": "Intermediate",
        "icon": ft.Icons.FITNESS_CENTER,
        "exercises": [
            exercise("Bench Press", "Chest", 4, "8 reps", 90),
            exercise("Incline Dumbbell Press", "Upper Chest", 3, "10 reps", 75),
            exercise("Overhead Press", "Shoulders", 3, "10 reps", 75),
            exercise("Lateral Raises", "Shoulders", 3, "12 reps", 45),
            exercise("Chest Fly", "Chest", 3, "12 reps", 45),
            exercise("Triceps Pushdown", "Triceps", 3, "12 reps", 45),
            exercise("Push-Ups", "Chest", 2, "15 reps", 45),
        ],
    },
    {
        "name": "Pull Day",
        "description": "Back and biceps",
        "duration": "40 min",
        "level": "Intermediate",
        "icon": ft.Icons.SPORTS_GYMNASTICS,
        "exercises": [
            exercise("Pull-Ups", "Back", 4, "6 reps", 90),
            exercise("Barbell Row", "Back", 4, "8 reps", 90),
            exercise("Lat Pulldown", "Back", 3, "10 reps", 60),
            exercise("Seated Cable Row", "Back", 3, "12 reps", 60),
            exercise("Face Pulls", "Rear Delts", 3, "15 reps", 45),
            exercise("Barbell Curl", "Biceps", 3, "10 reps", 45),
            exercise("Hammer Curl", "Biceps", 3, "12 reps", 45),
        ],
    },
    {
        "name": "Leg Day",
        "description": "Quads, hamstrings and glutes",
        "duration": "45 min",
        "level": "Intermediate",
        "icon": ft.Icons.DIRECTIONS_RUN,
        "exercises": [
            exercise("Back Squat", "Quads", 4, "8 reps", 90),
            exercise("Romanian Deadlift", "Hamstrings", 3, "10 reps", 90),
            exercise("Leg Press", "Quads", 3, "12 reps", 75),
            exercise("Walking Lunges", "Glutes", 3, "12 reps", 60),
            exercise("Leg Curl", "Hamstrings", 3, "12 reps", 60),
            exercise("Calf Raises", "Calves", 4, "15 reps", 45),
        ],
    },
]

# Exercise instructions: name -> (3 steps, 1 tip)
INSTRUCTIONS = {
    "Bodyweight Squats": (
        ["Stand with your feet shoulder-width apart, toes slightly out.",
         "Push your hips back and bend your knees until your thighs are parallel to the floor.",
         "Press through your heels to stand back up."],
        "Keep your chest up and your knees in line with your toes."),
    "Push-Ups": (
        ["Place your hands slightly wider than your shoulders, body in a straight line.",
         "Lower your chest until it is just above the floor.",
         "Push the floor away until your arms are straight."],
        "Don't let your hips sag. Drop to your knees if it's too hard."),
    "Dumbbell Rows": (
        ["Put one hand and one knee on a bench, holding a dumbbell in the other hand.",
         "Pull the dumbbell toward your hip, keeping your elbow close to your body.",
         "Lower it slowly until your arm is straight."],
        "Keep your back flat and avoid twisting your body."),
    "Shoulder Press": (
        ["Hold the dumbbells at shoulder height, palms facing forward.",
         "Press them overhead until your arms are straight.",
         "Lower them back to your shoulders with control."],
        "Tighten your core so you don't arch your lower back."),
    "Lunges": (
        ["Stand tall, then take a big step forward.",
         "Lower your back knee toward the floor until both knees are bent about 90 degrees.",
         "Push through your front foot to return to standing."],
        "Keep your front knee above your ankle, not past your toes."),
    "Plank": (
        ["Rest on your forearms with your elbows under your shoulders.",
         "Lift your body into a straight line from head to heels.",
         "Squeeze your core and glutes and hold."],
        "Don't let your hips sag or rise. Breathe steadily."),
    "Bench Press": (
        ["Lie on the bench with your feet flat and hands slightly wider than your shoulders.",
         "Lower the bar slowly to your mid-chest.",
         "Press the bar back up until your arms are straight."],
        "Keep your shoulder blades pinched. Use a spotter for heavy sets."),
    "Incline Dumbbell Press": (
        ["Set the bench to a 30 to 45 degree angle and hold the dumbbells at chest level.",
         "Press them up and slightly together above your upper chest.",
         "Lower them slowly back to the start."],
        "Don't bounce the weights off your chest."),
    "Overhead Press": (
        ["Hold the bar at your collarbone with your hands just outside your shoulders.",
         "Press the bar overhead, moving your head slightly forward as it passes.",
         "Lower the bar back to your collarbone."],
        "Squeeze your glutes to protect your lower back."),
    "Lateral Raises": (
        ["Stand holding light dumbbells at your sides.",
         "Raise your arms out to the sides until they reach shoulder height.",
         "Lower them slowly."],
        "Use a light weight and don't swing your body."),
    "Chest Fly": (
        ["Lie on a bench with the dumbbells above your chest, elbows slightly bent.",
         "Open your arms wide until you feel a stretch in your chest.",
         "Bring the dumbbells back together in a hugging motion."],
        "Keep the elbow bend the same the whole time."),
    "Triceps Pushdown": (
        ["Stand at a cable machine with the handle at chest height, elbows at your sides.",
         "Push the handle down until your arms are straight.",
         "Let it rise slowly back up."],
        "Keep your elbows pinned to your sides."),
    "Pull-Ups": (
        ["Hang from the bar with an overhand grip, slightly wider than your shoulders.",
         "Pull your chest toward the bar.",
         "Lower yourself all the way down with control."],
        "Use an assisted machine or a band if you can't do them yet."),
    "Barbell Row": (
        ["Hold the bar and hinge forward at your hips, back flat.",
         "Pull the bar to your lower ribs.",
         "Lower it slowly until your arms are straight."],
        "Don't jerk the weight with your lower back."),
    "Lat Pulldown": (
        ["Sit down and lock your thighs under the pads.",
         "Pull the bar down to your upper chest, driving your elbows down.",
         "Let the bar rise slowly back up."],
        "Don't lean back too far."),
    "Seated Cable Row": (
        ["Sit tall with your feet on the platform and knees slightly bent.",
         "Pull the handle to your stomach and squeeze your shoulder blades together.",
         "Straighten your arms slowly."],
        "Don't rock your body back and forth."),
    "Face Pulls": (
        ["Set the rope at face height and hold it with both hands.",
         "Pull it toward your face, elbows high, splitting the rope apart.",
         "Return slowly."],
        "Use a light weight and focus on your rear shoulders."),
    "Barbell Curl": (
        ["Stand holding the bar with an underhand grip.",
         "Curl the bar up while keeping your elbows at your sides.",
         "Lower it slowly."],
        "Don't swing your body to lift the weight."),
    "Hammer Curl": (
        ["Stand holding dumbbells with your palms facing each other.",
         "Curl them up toward your shoulders.",
         "Lower them slowly."],
        "Keep your wrists straight and elbows still."),
    "Back Squat": (
        ["Rest the bar on your upper back and set your feet shoulder-width apart.",
         "Sit down and back until your thighs are parallel to the floor.",
         "Drive up through your heels."],
        "Keep your chest up and core tight. Use safety bars in a rack."),
    "Romanian Deadlift": (
        ["Hold the bar at your thighs with a slight bend in your knees.",
         "Push your hips back and slide the bar down your legs until you feel a hamstring stretch.",
         "Drive your hips forward to stand tall."],
        "Keep your back flat and the bar close to your legs."),
    "Leg Press": (
        ["Sit in the machine with your feet shoulder-width apart on the platform.",
         "Lower the platform until your knees are bent about 90 degrees.",
         "Press it back up without locking your knees."],
        "Keep your hips and lower back against the seat."),
    "Walking Lunges": (
        ["Step forward into a lunge, lowering your back knee toward the floor.",
         "Push off your back foot and step forward into the next lunge.",
         "Keep alternating legs as you walk."],
        "Take steps long enough that your front knee stays over your ankle."),
    "Leg Curl": (
        ["Lie or sit on the machine with the pad just above your heels.",
         "Curl your heels toward your glutes.",
         "Return slowly to the start."],
        "Don't lift your hips off the pad."),
    "Calf Raises": (
        ["Stand with the balls of your feet on the edge of a step.",
         "Rise onto your toes as high as you can and pause.",
         "Lower your heels below the step for a full stretch."],
        "Move slowly. Don't bounce."),
}

DEFAULT_INSTRUCTIONS = (
    ["Set up with good posture.", "Move slowly and with control.", "Breathe steadily."],
    "Quality reps matter more than heavy weight.",
)


def all_exercises():
    """A list of every unique exercise (used by the Exercise Library)."""
    found = {}
    for workout in WORKOUTS:
        for ex in workout["exercises"]:
            found.setdefault(ex["name"], {"name": ex["name"], "muscle": ex["muscle"]})
    return sorted(found.values(), key=lambda item: item["name"])


# ---------------------------------------------------------------
# 2b. 30-DAY PLAN GENERATOR (logic only, there are no screens in this section)
#
#     INPUT : the onboarding answers.
#     OUTPUT: a list of exactly 30 small "day" dictionaries.
#
#     A plan day does NOT copy exercise data. It points at a workout by name
#     (for example "Full Body") and lists which of its exercises to do.
#     find_workout(name) + plan_day_workout(day) turn it back into the same
#     kind of workout dictionary the detail screen and the player already use.
# ---------------------------------------------------------------
PLAN_LENGTH = 30
MIN_EXERCISES = 3                       # a workout day always has at least 3 exercises
MAX_EXTRA_SETS = 2                      # a workout can get up to 2 more sets per exercise to fill the time
LEVEL_NAMES = ["Complete beginner", "Beginner", "Intermediate", "Advanced"]
SETS_CAP = [4, 5, 6, 6]                 # most sets per exercise, by experience level
# (lowest minutes, highest minutes) for each answer to "How long can each workout be?"
DURATION_RANGE = {
    "15–20 minutes": (15, 20),
    "20–30 minutes": (20, 30),
    "30–45 minutes": (30, 45),
    "45–60 minutes": (45, 60),
    "60+ minutes": (60, 80),
}
# Equipment kinds, strongest first: gym > barbell > dumbbells > bands > none
TIER_ORDER = ["gym", "barbell", "dumbbells", "bands", "none"]


def exercise_info(muscle, equip="none", level=0, timed=False, avoid=()):
    """Facts about one exercise.
    equip = what it needs, level = lowest experience level (0-3) it suits,
    timed = counted in seconds, avoid = body areas it puts stress on."""
    return {"muscle": muscle, "equip": equip, "level": level, "timed": timed, "avoid": set(avoid)}


EXERCISE_INFO = {
    # --- Exercises already used in the programs ---
    "Bodyweight Squats": exercise_info("Legs", "none", 0, avoid=("knees",)),
    "Push-Ups": exercise_info("Chest", "none", 1, avoid=("wrists", "shoulders")),
    "Dumbbell Rows": exercise_info("Back", "dumbbells", 0),
    "Shoulder Press": exercise_info("Shoulders", "dumbbells", 0, avoid=("shoulders",)),
    "Lunges": exercise_info("Legs", "none", 0, avoid=("knees",)),
    "Plank": exercise_info("Core", "none", 0, timed=True),
    "Bench Press": exercise_info("Chest", "barbell", 1, avoid=("shoulders", "wrists")),
    "Incline Dumbbell Press": exercise_info("Upper Chest", "gym", 1, avoid=("shoulders",)),
    "Overhead Press": exercise_info("Shoulders", "barbell", 1, avoid=("shoulders", "lower back")),
    "Lateral Raises": exercise_info("Shoulders", "dumbbells", 0, avoid=("shoulders",)),
    "Chest Fly": exercise_info("Chest", "gym", 1, avoid=("shoulders",)),
    "Triceps Pushdown": exercise_info("Triceps", "gym", 0, avoid=("wrists",)),
    "Pull-Ups": exercise_info("Back", "gym", 2, avoid=("shoulders", "wrists")),
    "Barbell Row": exercise_info("Back", "barbell", 2, avoid=("lower back",)),
    "Lat Pulldown": exercise_info("Back", "gym", 0, avoid=("shoulders",)),
    "Seated Cable Row": exercise_info("Back", "gym", 0),
    "Face Pulls": exercise_info("Rear Delts", "gym", 0),
    "Barbell Curl": exercise_info("Biceps", "barbell", 1, avoid=("wrists",)),
    "Hammer Curl": exercise_info("Biceps", "dumbbells", 0),
    "Back Squat": exercise_info("Quads", "barbell", 2, avoid=("knees", "lower back")),
    "Romanian Deadlift": exercise_info("Hamstrings", "barbell", 2, avoid=("lower back",)),
    "Leg Press": exercise_info("Quads", "gym", 0, avoid=("knees",)),
    "Walking Lunges": exercise_info("Glutes", "none", 1, avoid=("knees",)),
    "Leg Curl": exercise_info("Hamstrings", "gym", 0),
    "Calf Raises": exercise_info("Calves", "none", 0),
    # --- Bodyweight ---
    "Knee Push-Ups": exercise_info("Chest", "none", 0, avoid=("wrists", "shoulders")),
    "Glute Bridge": exercise_info("Glutes", "none", 0),
    "Wall Sit": exercise_info("Quads", "none", 0, timed=True, avoid=("knees",)),
    "Close-Grip Push-Ups": exercise_info("Triceps", "none", 1, avoid=("wrists", "shoulders")),
    "Pike Push-Ups": exercise_info("Shoulders", "none", 1, avoid=("wrists", "shoulders")),
    "Superman": exercise_info("Back", "none", 0, avoid=("lower back",)),
    "Bird Dog": exercise_info("Core", "none", 0, avoid=("wrists",)),
    "Dead Bug": exercise_info("Core", "none", 0),
    "Bicycle Crunches": exercise_info("Core", "none", 0),
    "Side Plank": exercise_info("Core", "none", 1, timed=True, avoid=("shoulders", "wrists")),
    "Mountain Climbers": exercise_info("Cardio", "none", 1, timed=True, avoid=("wrists", "shoulders", "knees")),
    "Jumping Jacks": exercise_info("Cardio", "none", 0, timed=True, avoid=("knees",)),
    "High Knees": exercise_info("Cardio", "none", 0, timed=True, avoid=("knees",)),
    "Burpees": exercise_info("Full Body", "none", 2, timed=True, avoid=("knees", "wrists", "shoulders", "lower back")),
    "Cat-Cow": exercise_info("Mobility", "none", 0, timed=True),
    "Child's Pose": exercise_info("Mobility", "none", 0, timed=True),
    "Hip Flexor Stretch": exercise_info("Mobility", "none", 0, timed=True),
    "Marching in Place": exercise_info("Cardio", "none", 0, timed=True),
    # --- Resistance bands ---
    "Band Rows": exercise_info("Back", "bands", 0),
    "Band Pull-Aparts": exercise_info("Rear Delts", "bands", 0),
    "Band Chest Press": exercise_info("Chest", "bands", 0, avoid=("shoulders",)),
    "Band Shoulder Press": exercise_info("Shoulders", "bands", 0, avoid=("shoulders",)),
    "Band Squats": exercise_info("Legs", "bands", 0, avoid=("knees",)),
    "Band Curls": exercise_info("Biceps", "bands", 0),
    "Band Triceps Extension": exercise_info("Triceps", "bands", 0),
    "Band Deadlift": exercise_info("Hamstrings", "bands", 0, avoid=("lower back",)),
    "Band Lateral Walks": exercise_info("Glutes", "bands", 0, avoid=("knees",)),
    # --- Dumbbells ---
    "Goblet Squat": exercise_info("Quads", "dumbbells", 0, avoid=("knees",)),
    "Dumbbell Romanian Deadlift": exercise_info("Hamstrings", "dumbbells", 1, avoid=("lower back",)),
    "Dumbbell Floor Press": exercise_info("Chest", "dumbbells", 0, avoid=("shoulders",)),
    "Dumbbell Curl": exercise_info("Biceps", "dumbbells", 0),
    "Overhead Triceps Extension": exercise_info("Triceps", "dumbbells", 0, avoid=("shoulders",)),
    "Dumbbell Glute Bridge": exercise_info("Glutes", "dumbbells", 0),
    "Dumbbell Reverse Lunges": exercise_info("Legs", "dumbbells", 1, avoid=("knees",)),
    # --- Barbell ---
    "Deadlift": exercise_info("Back", "barbell", 2, avoid=("lower back",)),
    "Barbell Hip Thrust": exercise_info("Glutes", "barbell", 1),
    # --- Gym machines and cables ---
    "Leg Extension": exercise_info("Quads", "gym", 0, avoid=("knees",)),
    "Machine Chest Press": exercise_info("Chest", "gym", 0, avoid=("shoulders",)),
    "Machine Shoulder Press": exercise_info("Shoulders", "gym", 0, avoid=("shoulders",)),
    "Cable Crunch": exercise_info("Core", "gym", 1),
}

INSTRUCTIONS.update({
    "Knee Push-Ups": (
        ["Start on your hands and knees, hands slightly wider than your shoulders.",
         "Lower your chest toward the floor, keeping a straight line from knees to head.",
         "Push back up."],
        "A great step on the way to full push-ups."),
    "Glute Bridge": (
        ["Lie on your back with your knees bent and feet flat.",
         "Squeeze your glutes and lift your hips until your body is in a straight line.",
         "Lower slowly."],
        "Don't over-arch your lower back at the top."),
    "Wall Sit": (
        ["Lean your back against a wall and slide down until your knees are bent about 90 degrees.",
         "Keep your feet flat and your knees above your ankles.",
         "Hold for the time shown."],
        "Press your back into the wall and breathe steadily."),
    "Close-Grip Push-Ups": (
        ["Place your hands under your chest, closer than shoulder-width.",
         "Lower your chest, keeping your elbows close to your ribs.",
         "Push back up."],
        "Drop to your knees if you need to."),
    "Pike Push-Ups": (
        ["Start in a push-up position, walk your feet in and lift your hips into an upside-down V.",
         "Bend your elbows to lower the top of your head toward the floor.",
         "Press back up."],
        "Move slowly. This one works your shoulders hard."),
    "Superman": (
        ["Lie face down with your arms stretched out in front.",
         "Lift your arms, chest and legs slightly off the floor.",
         "Hold for a second, then lower."],
        "Lift only a little and keep your neck relaxed."),
    "Bird Dog": (
        ["Start on your hands and knees with a flat back.",
         "Reach one arm forward while stretching the opposite leg back.",
         "Return and switch sides."],
        "Move slowly and keep your hips level."),
    "Dead Bug": (
        ["Lie on your back with your arms up and knees bent over your hips.",
         "Lower one arm and the opposite leg toward the floor.",
         "Return and switch sides."],
        "Keep your lower back gently pressed into the floor."),
    "Bicycle Crunches": (
        ["Lie on your back with your hands lightly behind your head.",
         "Bring one knee in while turning the opposite elbow toward it.",
         "Alternate sides in a pedaling motion."],
        "Twist from your torso and don't pull on your neck."),
    "Side Plank": (
        ["Lie on your side with your elbow under your shoulder.",
         "Lift your hips so your body is in a straight line.",
         "Hold, then switch sides."],
        "Keep your hips high and your feet stacked."),
    "Mountain Climbers": (
        ["Start in a high plank position.",
         "Drive one knee toward your chest, then quickly switch legs.",
         "Keep a steady pace."],
        "Keep your hips low and your core tight."),
    "Jumping Jacks": (
        ["Stand with your feet together and arms at your sides.",
         "Jump your feet out while raising your arms overhead.",
         "Jump back to the start."],
        "Land softly. Step side to side if you prefer no jumping."),
    "High Knees": (
        ["Stand tall and jog in place.",
         "Lift your knees toward hip height.",
         "Pump your arms."],
        "Stay light on your feet."),
    "Burpees": (
        ["Squat down and place your hands on the floor.",
         "Kick your feet back to a plank, then bring them back in.",
         "Stand up, or jump, and repeat."],
        "Step instead of jumping to make it easier."),
    "Cat-Cow": (
        ["Start on your hands and knees.",
         "Round your back up toward the ceiling, then arch it down as you look up.",
         "Move slowly with your breathing."],
        "Stay in a comfortable range."),
    "Child's Pose": (
        ["Kneel and sit back toward your heels.",
         "Reach your arms forward and rest your forehead down.",
         "Breathe slowly and relax."],
        "Spread your knees wider if that feels better."),
    "Hip Flexor Stretch": (
        ["Kneel on one knee with the other foot in front.",
         "Tuck your tailbone and gently shift your weight forward.",
         "Hold, then switch sides."],
        "Keep your torso upright."),
    "Marching in Place": (
        ["Stand tall.",
         "Lift your knees one at a time in a steady march.",
         "Swing your arms naturally."],
        "An easy way to get your body gently moving."),
    "Band Rows": (
        ["Sit with the band around your feet, or anchor it at chest height.",
         "Pull the handles toward your ribs, squeezing your shoulder blades together.",
         "Return slowly."],
        "Keep your shoulders down and back."),
    "Band Pull-Aparts": (
        ["Hold the band in front of you at chest height with straight arms.",
         "Pull it apart until it touches your chest.",
         "Return slowly."],
        "Squeeze your shoulder blades together."),
    "Band Chest Press": (
        ["Anchor the band behind you at chest height.",
         "Press the handles forward until your arms are straight.",
         "Return slowly."],
        "Keep your wrists straight."),
    "Band Shoulder Press": (
        ["Stand on the band with the handles at shoulder height.",
         "Press overhead until your arms are straight.",
         "Lower with control."],
        "Brace your core so your back doesn't arch."),
    "Band Squats": (
        ["Stand on the band with your feet shoulder-width apart, holding it at your shoulders.",
         "Sit back and down into a squat.",
         "Stand back up."],
        "Push your knees out slightly."),
    "Band Curls": (
        ["Stand on the band holding the handles at your sides.",
         "Curl your hands toward your shoulders.",
         "Lower slowly."],
        "Keep your elbows tucked in."),
    "Band Triceps Extension": (
        ["Anchor the band overhead or hold it behind your back.",
         "Straighten your arms, keeping your elbows still.",
         "Return slowly."],
        "Only your forearms should move."),
    "Band Deadlift": (
        ["Stand on the band holding the handles at your thighs.",
         "Push your hips back and lower your torso with a flat back.",
         "Drive your hips forward to stand."],
        "Keep the band close to your legs."),
    "Band Lateral Walks": (
        ["Put the band around your thighs and bend your knees slightly.",
         "Step sideways, keeping tension on the band.",
         "Walk in both directions."],
        "Don't let your knees cave inward."),
    "Goblet Squat": (
        ["Hold one dumbbell against your chest.",
         "Sit down between your knees until your thighs are parallel to the floor.",
         "Stand back up."],
        "Keep your chest tall."),
    "Dumbbell Romanian Deadlift": (
        ["Hold dumbbells in front of your thighs.",
         "Push your hips back and slide the weights down your legs.",
         "Drive your hips forward to stand."],
        "Keep your back flat."),
    "Dumbbell Floor Press": (
        ["Lie on the floor with the dumbbells above your chest.",
         "Lower until your upper arms touch the floor.",
         "Press back up."],
        "No bench needed. Keep your wrists straight."),
    "Dumbbell Curl": (
        ["Stand holding dumbbells with your palms facing forward.",
         "Curl them toward your shoulders.",
         "Lower slowly."],
        "Don't swing your body."),
    "Overhead Triceps Extension": (
        ["Hold one dumbbell overhead with both hands.",
         "Bend your elbows to lower it behind your head.",
         "Straighten your arms."],
        "Keep your elbows pointing forward."),
    "Dumbbell Glute Bridge": (
        ["Lie on your back with a dumbbell resting on your hips.",
         "Squeeze your glutes and lift your hips.",
         "Lower slowly."],
        "Pause for a second at the top."),
    "Dumbbell Reverse Lunges": (
        ["Hold dumbbells at your sides.",
         "Step back and lower your back knee toward the floor.",
         "Push through your front foot to return."],
        "Keep your front heel on the floor."),
    "Deadlift": (
        ["Stand with the bar over your mid-foot and grip just outside your legs.",
         "Keep your back flat and push the floor away to stand up.",
         "Lower the bar under control."],
        "Start light and focus on form."),
    "Barbell Hip Thrust": (
        ["Sit with your upper back against a bench and the bar over your hips.",
         "Drive your hips up until your body is in a straight line.",
         "Lower slowly."],
        "Tuck your chin and squeeze your glutes."),
    "Leg Extension": (
        ["Sit in the machine with the pad resting on your shins.",
         "Straighten your legs.",
         "Lower slowly."],
        "Don't slam your knees straight."),
    "Machine Chest Press": (
        ["Adjust the seat so the handles are at chest height.",
         "Press forward until your arms are straight.",
         "Return slowly."],
        "Keep your shoulders back."),
    "Machine Shoulder Press": (
        ["Adjust the seat so the handles are at shoulder height.",
         "Press upward until your arms are straight.",
         "Lower slowly."],
        "Don't shrug your shoulders."),
    "Cable Crunch": (
        ["Kneel facing a cable machine with the rope by your head.",
         "Curl your ribs toward your hips.",
         "Return slowly."],
        "Move from your abs, not your hips."),
})


# ---------- time estimate (the same formula is used for every workout) ----------
def exercise_seconds(ex, sets):
    """Seconds for one exercise: work + rest for every set, plus 30s to set up."""
    reps = ex["reps"]
    work = int(reps.split()[0]) if reps.endswith("sec") else 40
    return sets * (work + ex["rest"]) + 30


def day_sets(base_sets, adjust, cap, is_light):
    """Sets to do for one exercise on a plan day (never fewer than 2)."""
    sets = base_sets + adjust - (1 if is_light else 0)
    return max(2, min(sets, cap))


# ---------- extra workouts used by the plan ----------
# These use exactly the same format as WORKOUTS. They are used by the 30-day
# plan for people who have no equipment, only bands, only a barbell, etc.
# (Your 4 existing programs need dumbbells or a full gym.)
KIND_TITLE = {
    "FULL": "Full Body", "UPPER": "Upper Body", "LOWER": "Lower Body",
    "PUSH": "Push Day", "PULL": "Pull Day", "LEGS": "Leg Day",
    "CORE": "Core & Cardio", "RECOVERY": "Active Recovery",
}
KIND_ICON = {
    "FULL": ft.Icons.ACCESSIBILITY_NEW, "UPPER": ft.Icons.FITNESS_CENTER,
    "LOWER": ft.Icons.DIRECTIONS_RUN, "PUSH": ft.Icons.FITNESS_CENTER,
    "PULL": ft.Icons.SPORTS_GYMNASTICS, "LEGS": ft.Icons.DIRECTIONS_RUN,
    "CORE": ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, "RECOVERY": ft.Icons.SELF_IMPROVEMENT,
}
# kind = the type of session, min_level = lowest experience level (0-3) it suits
PROGRAM_META = {
    "Full Body": {"kind": "FULL", "min_level": 0},
    "Push Day": {"kind": "PUSH", "min_level": 2},
    "Pull Day": {"kind": "PULL", "min_level": 2},
    "Leg Day": {"kind": "LEGS", "min_level": 2},
}


def make_program(name, kind, min_level, description, rows):
    """Build a workout dictionary. rows = (exercise name, sets, reps, rest seconds)."""
    exercises = [exercise(n, EXERCISE_INFO[n]["muscle"], s, r, rest) for n, s, r, rest in rows]
    seconds = sum(exercise_seconds(ex, ex["sets"]) for ex in exercises)
    PROGRAM_META[name] = {"kind": kind, "min_level": min_level}
    return {
        "name": name,
        "description": description,
        "duration": f"{max(10, 5 * round(seconds / 300))} min",
        "level": "Beginner" if min_level < 2 else "Intermediate",
        "icon": KIND_ICON[kind],
        "exercises": exercises,
    }


PLAN_PROGRAMS = [
    # --- Bodyweight (no equipment) ---
    make_program("Bodyweight Full Body A", "FULL", 0, "Whole body, no equipment", [
        ("Bodyweight Squats", 3, "12 reps", 60), ("Knee Push-Ups", 3, "10 reps", 60),
        ("Glute Bridge", 3, "12 reps", 45), ("Superman", 3, "10 reps", 45),
        ("Lunges", 3, "10 reps", 60), ("Plank", 3, "30 sec", 45), ("Dead Bug", 3, "10 reps", 45),
        ("Bird Dog", 3, "10 reps", 45), ("Bicycle Crunches", 3, "15 reps", 40),
        ("Calf Raises", 3, "15 reps", 45)]),
    make_program("Bodyweight Full Body B", "FULL", 0, "Whole body, no equipment", [
        ("Push-Ups", 3, "10 reps", 60), ("Wall Sit", 3, "30 sec", 45),
        ("Walking Lunges", 3, "12 reps", 60), ("Glute Bridge", 3, "15 reps", 45),
        ("Close-Grip Push-Ups", 3, "8 reps", 60), ("Side Plank", 3, "20 sec", 40),
        ("Calf Raises", 3, "15 reps", 45), ("Bicycle Crunches", 3, "15 reps", 40),
        ("Superman", 3, "12 reps", 45), ("Dead Bug", 3, "10 reps", 45)]),
    make_program("Bodyweight Upper Body", "UPPER", 0, "Chest, back and arms, no equipment", [
        ("Knee Push-Ups", 3, "10 reps", 60), ("Push-Ups", 3, "8 reps", 60),
        ("Close-Grip Push-Ups", 3, "8 reps", 60), ("Pike Push-Ups", 3, "8 reps", 60),
        ("Superman", 3, "12 reps", 45), ("Plank", 3, "30 sec", 45), ("Dead Bug", 3, "10 reps", 45),
        ("Bird Dog", 3, "10 reps", 45), ("Side Plank", 3, "20 sec", 40)]),
    make_program("Bodyweight Lower Body", "LOWER", 0, "Legs and glutes, no equipment", [
        ("Bodyweight Squats", 4, "15 reps", 60), ("Glute Bridge", 3, "15 reps", 45),
        ("Lunges", 3, "10 reps", 60), ("Wall Sit", 3, "30 sec", 45),
        ("Walking Lunges", 3, "12 reps", 60), ("Calf Raises", 4, "15 reps", 45),
        ("Plank", 3, "30 sec", 45), ("Dead Bug", 3, "10 reps", 45), ("Bird Dog", 3, "10 reps", 45)]),
    make_program("Core & Cardio", "CORE", 0, "Core strength and conditioning", [
        ("Jumping Jacks", 3, "40 sec", 30), ("Plank", 3, "30 sec", 30),
        ("High Knees", 3, "30 sec", 30), ("Dead Bug", 3, "10 reps", 30),
        ("Mountain Climbers", 3, "30 sec", 30), ("Bicycle Crunches", 3, "15 reps", 30),
        ("Side Plank", 3, "20 sec", 30), ("Burpees", 3, "8 reps", 45),
        ("Marching in Place", 3, "45 sec", 30), ("Bird Dog", 3, "10 reps", 30)]),
    make_program("Active Recovery", "RECOVERY", 0, "Gentle movement and stretching", [
        ("Cat-Cow", 2, "40 sec", 15), ("Child's Pose", 2, "30 sec", 15),
        ("Hip Flexor Stretch", 2, "30 sec", 15), ("Bird Dog", 2, "8 reps", 20),
        ("Glute Bridge", 2, "10 reps", 20), ("Marching in Place", 2, "60 sec", 15)]),
    # --- Resistance bands ---
    make_program("Band Full Body", "FULL", 0, "Whole body with resistance bands", [
        ("Band Squats", 3, "12 reps", 60), ("Band Chest Press", 3, "12 reps", 60),
        ("Band Rows", 3, "12 reps", 60), ("Band Shoulder Press", 3, "10 reps", 60),
        ("Band Deadlift", 3, "12 reps", 60), ("Band Curls", 3, "12 reps", 45),
        ("Plank", 3, "30 sec", 45), ("Band Pull-Aparts", 3, "15 reps", 45),
        ("Band Triceps Extension", 3, "12 reps", 45), ("Glute Bridge", 3, "15 reps", 45)]),
    make_program("Band Upper Body", "UPPER", 0, "Chest, back and arms with bands", [
        ("Band Chest Press", 3, "12 reps", 60), ("Band Rows", 3, "12 reps", 60),
        ("Band Shoulder Press", 3, "10 reps", 60), ("Band Pull-Aparts", 3, "15 reps", 45),
        ("Band Curls", 3, "12 reps", 45), ("Band Triceps Extension", 3, "12 reps", 45),
        ("Plank", 3, "30 sec", 45), ("Dead Bug", 3, "10 reps", 45), ("Bird Dog", 3, "10 reps", 45)]),
    make_program("Band Lower Body", "LOWER", 0, "Legs and glutes with bands", [
        ("Band Squats", 4, "12 reps", 60), ("Band Deadlift", 3, "12 reps", 60),
        ("Band Lateral Walks", 3, "12 reps", 45), ("Glute Bridge", 3, "15 reps", 45),
        ("Lunges", 3, "10 reps", 60), ("Calf Raises", 4, "15 reps", 45),
        ("Plank", 3, "30 sec", 45), ("Dead Bug", 3, "10 reps", 45), ("Bird Dog", 3, "10 reps", 45)]),
    # --- Dumbbells (your existing "Full Body" is the first dumbbell full-body workout) ---
    make_program("Dumbbell Full Body", "FULL", 0, "Whole body with dumbbells", [
        ("Goblet Squat", 3, "12 reps", 60), ("Dumbbell Floor Press", 3, "10 reps", 60),
        ("Dumbbell Rows", 3, "12 reps", 60), ("Dumbbell Romanian Deadlift", 3, "10 reps", 60),
        ("Shoulder Press", 3, "10 reps", 60), ("Dumbbell Curl", 3, "12 reps", 45),
        ("Dumbbell Glute Bridge", 3, "12 reps", 45), ("Plank", 3, "30 sec", 45),
        ("Lateral Raises", 3, "12 reps", 45), ("Overhead Triceps Extension", 3, "12 reps", 45)]),
    make_program("Dumbbell Upper Body", "UPPER", 0, "Chest, back, shoulders and arms", [
        ("Dumbbell Floor Press", 3, "10 reps", 60), ("Dumbbell Rows", 3, "12 reps", 60),
        ("Shoulder Press", 3, "10 reps", 60), ("Lateral Raises", 3, "12 reps", 45),
        ("Dumbbell Curl", 3, "12 reps", 45), ("Overhead Triceps Extension", 3, "12 reps", 45),
        ("Plank", 3, "30 sec", 45), ("Hammer Curl", 3, "12 reps", 45), ("Push-Ups", 3, "10 reps", 60),
        ("Dead Bug", 3, "10 reps", 45)]),
    make_program("Dumbbell Lower Body", "LOWER", 0, "Legs and glutes with dumbbells", [
        ("Goblet Squat", 4, "12 reps", 60), ("Dumbbell Romanian Deadlift", 3, "10 reps", 60),
        ("Dumbbell Reverse Lunges", 3, "10 reps", 60), ("Dumbbell Glute Bridge", 3, "12 reps", 45),
        ("Calf Raises", 4, "15 reps", 45), ("Plank", 3, "30 sec", 45),
        ("Lunges", 3, "10 reps", 60), ("Dead Bug", 3, "10 reps", 45), ("Bird Dog", 3, "10 reps", 45)]),
    # --- Barbell ---
    make_program("Barbell Full Body", "FULL", 1, "Whole body with a barbell", [
        ("Back Squat", 4, "8 reps", 90), ("Bench Press", 4, "8 reps", 90),
        ("Barbell Row", 3, "8 reps", 75), ("Romanian Deadlift", 3, "8 reps", 90),
        ("Overhead Press", 3, "8 reps", 75), ("Barbell Hip Thrust", 3, "10 reps", 60),
        ("Plank", 3, "30 sec", 45), ("Barbell Curl", 3, "10 reps", 45), ("Lunges", 3, "10 reps", 60),
        ("Dead Bug", 3, "10 reps", 45)]),
    make_program("Barbell Upper Body", "UPPER", 1, "Chest, back, shoulders and arms", [
        ("Bench Press", 4, "8 reps", 90), ("Barbell Row", 4, "8 reps", 90),
        ("Overhead Press", 3, "8 reps", 75), ("Barbell Curl", 3, "10 reps", 45),
        ("Push-Ups", 3, "12 reps", 45), ("Plank", 3, "40 sec", 45), ("Dead Bug", 3, "10 reps", 45),
        ("Bicycle Crunches", 3, "15 reps", 40), ("Side Plank", 3, "20 sec", 40)]),
    make_program("Barbell Lower Body", "LOWER", 1, "Legs and glutes with a barbell", [
        ("Back Squat", 4, "8 reps", 90), ("Romanian Deadlift", 3, "8 reps", 90),
        ("Barbell Hip Thrust", 3, "10 reps", 60), ("Walking Lunges", 3, "12 reps", 60),
        ("Calf Raises", 4, "15 reps", 45), ("Plank", 3, "30 sec", 45), ("Lunges", 3, "10 reps", 60),
        ("Dead Bug", 3, "10 reps", 45), ("Bicycle Crunches", 3, "15 reps", 40)]),
    # --- Full gym (machines and cables) ---
    make_program("Gym Full Body", "FULL", 0, "Whole body on machines and cables", [
        ("Leg Press", 3, "12 reps", 75), ("Machine Chest Press", 3, "12 reps", 60),
        ("Lat Pulldown", 3, "12 reps", 60), ("Machine Shoulder Press", 3, "10 reps", 60),
        ("Leg Curl", 3, "12 reps", 60), ("Seated Cable Row", 3, "12 reps", 60),
        ("Cable Crunch", 3, "15 reps", 45), ("Triceps Pushdown", 3, "12 reps", 45),
        ("Hammer Curl", 3, "12 reps", 45), ("Plank", 3, "30 sec", 45)]),
    make_program("Gym Upper Body", "UPPER", 0, "Chest, back, shoulders and arms", [
        ("Machine Chest Press", 3, "12 reps", 60), ("Lat Pulldown", 3, "12 reps", 60),
        ("Seated Cable Row", 3, "12 reps", 60), ("Machine Shoulder Press", 3, "10 reps", 60),
        ("Triceps Pushdown", 3, "12 reps", 45), ("Hammer Curl", 3, "12 reps", 45),
        ("Face Pulls", 3, "15 reps", 45), ("Cable Crunch", 3, "15 reps", 45), ("Plank", 3, "30 sec", 45)]),
    make_program("Gym Lower Body", "LOWER", 0, "Legs and glutes on machines", [
        ("Leg Press", 4, "12 reps", 75), ("Leg Extension", 3, "12 reps", 60),
        ("Leg Curl", 3, "12 reps", 60), ("Dumbbell Romanian Deadlift", 3, "10 reps", 60),
        ("Walking Lunges", 3, "12 reps", 60), ("Calf Raises", 4, "15 reps", 45),
        ("Cable Crunch", 3, "15 reps", 45), ("Plank", 3, "30 sec", 45), ("Bird Dog", 3, "10 reps", 45)]),
]

ALL_PROGRAMS = WORKOUTS + PLAN_PROGRAMS


def find_workout(name):
    """Find a workout by name in your programs OR the plan's extra programs."""
    for workout in ALL_PROGRAMS:
        if workout["name"] == name:
            return workout
    return None


def program_requires(program):
    """The kinds of equipment a workout needs (not counting bodyweight)."""
    return {EXERCISE_INFO[ex["name"]]["equip"] for ex in program["exercises"]} - {"none"}


def program_tier(program):
    """The strongest equipment a workout needs ('none' for bodyweight)."""
    needs = program_requires(program)
    return next((t for t in TIER_ORDER if t in needs), "none")


# ---------- goals and weekly structure ----------
# goal -> (group, short focus label shown on plan days)
GOAL_GROUP = {
    "Lose weight": ("cond", "Conditioning"),
    "Build muscle": ("muscle", "Muscle building"),
    "Get stronger": ("strength", "Strength"),
    "Improve fitness": ("fit", "Fitness"),
    "Build a healthy routine": ("routine", "Healthy routine"),
    "Maintain weight": ("balanced", "Balanced training"),
}

# The workout types for one week, by goal group and days per week.
# FULL = full body, CORE = core & cardio, PUSH/PULL/LEGS = the 3-way split.
TEMPLATES = {
    "cond": {   # lose weight: lots of full-body and conditioning
        2: ["FULL", "CORE"],
        3: ["FULL", "CORE", "FULL"],
        4: ["FULL", "CORE", "FULL", "CORE"],
        5: ["FULL", "CORE", "FULL", "CORE", "FULL"],
        6: ["FULL", "CORE", "UPPER", "CORE", "LOWER", "FULL"],
    },
    "fit": {    # improve fitness: balanced full-body, strength and conditioning
        2: ["FULL", "CORE"],
        3: ["FULL", "CORE", "FULL"],
        4: ["FULL", "UPPER", "CORE", "LOWER"],
        5: ["FULL", "UPPER", "CORE", "LOWER", "FULL"],
        6: ["FULL", "UPPER", "CORE", "LOWER", "CORE", "FULL"],
    },
    "muscle": { # build muscle: resistance-training splits
        2: ["FULL", "FULL"],
        3: ["UPPER", "LOWER", "FULL"],
        4: ["UPPER", "LOWER", "UPPER", "LOWER"],
        5: ["PUSH", "PULL", "LEGS", "UPPER", "LOWER"],
        6: ["PUSH", "PULL", "LEGS", "PUSH", "PULL", "LEGS"],
    },
    "strength": {  # get stronger: heavy compound days, lower body first
        2: ["FULL", "FULL"],
        3: ["FULL", "LOWER", "UPPER"],
        4: ["LOWER", "UPPER", "LOWER", "UPPER"],
        5: ["LOWER", "UPPER", "FULL", "LOWER", "UPPER"],
        6: ["LOWER", "UPPER", "FULL", "LOWER", "UPPER", "FULL"],
    },
    "routine": {  # healthy routine: simple, sustainable, plenty of easy days
        2: ["FULL", "FULL"],
        3: ["FULL", "CORE", "FULL"],
        4: ["FULL", "CORE", "FULL", "LOWER"],
        5: ["FULL", "CORE", "UPPER", "CORE", "LOWER"],
        6: ["FULL", "CORE", "UPPER", "LOWER", "CORE", "FULL"],
    },
    "balanced": {  # maintain weight: even mix
        2: ["FULL", "FULL"],
        3: ["FULL", "UPPER", "LOWER"],
        4: ["UPPER", "LOWER", "FULL", "CORE"],
        5: ["FULL", "UPPER", "LOWER", "CORE", "FULL"],
        6: ["FULL", "UPPER", "LOWER", "FULL", "UPPER", "LOWER"],
    },
}
# Without a full gym (or if you're not Intermediate+) the 3-way split becomes simpler types.
SIMPLER = {"PUSH": "UPPER", "PULL": "FULL", "LEGS": "LOWER"}
# Which of the 7 days in a week are training days (0 = first day of the week).
WEEK_LAYOUT = {
    2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4],
    5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 4, 5, 6], 7: [0, 1, 2, 4, 5],
}


def equipment_tokens(equipment):
    """Which kinds of equipment the user can use (from the onboarding answer)."""
    tokens = {"none"}
    if "Full gym" in equipment:
        return {"none", "bands", "dumbbells", "barbell", "gym"}
    if "Dumbbells" in equipment:
        tokens.add("dumbbells")
    if "Resistance bands" in equipment:
        tokens.add("bands")
    if "Barbell" in equipment:
        tokens.add("barbell")
    return tokens


def plan_context(answers):
    """Turn the onboarding answers into simple settings for the generator."""
    goal = answers.get("goal") if answers.get("goal") in GOAL_GROUP else "Improve fitness"
    level = LEVEL_NAMES.index(answers["level"]) if answers.get("level") in LEVEL_NAMES else 1
    low, high = DURATION_RANGE.get(answers.get("duration"), (30, 45))
    try:
        days = min(7, max(2, int(answers.get("days"))))
    except (TypeError, ValueError):
        days = 3
    movement = answers.get("movement") or {}
    mode = movement.get("mode") if movement.get("mode") in ("avoid", "light") else "none"
    group, focus = GOAL_GROUP[goal]
    tokens = equipment_tokens(answers.get("equipment") or ["No equipment"])

    # Which equipment tier we prefer when several workouts fit (lower number = preferred).
    rank = {"gym": 0, "barbell": 1, "dumbbells": 2, "bands": 3, "none": 4}
    if group == "strength":
        rank = {"barbell": 0, "gym": 1, "dumbbells": 2, "bands": 3, "none": 4}
    if answers.get("location") == "Home":
        rank["gym"] = 5  # at home, prefer home-friendly workouts (still allowed if you have a full gym)

    return {
        "goal": goal, "group": group, "focus": focus, "level": level, "days": days,
        "low": low, "high": high, "tokens": tokens, "rank": rank,
        "mode": mode, "areas": {str(a).lower() for a in (movement.get("areas") or [])},
        "cap": SETS_CAP[level],
        # beginners and "healthy routine" start with one set fewer per exercise
        "base_adjust": -1 if (level == 0 or group == "routine") else 0,
        "split_ok": level >= 2 and "gym" in tokens,   # PUSH / PULL / LEGS days
    }


def week_kinds(ctx):
    """A list of 7 items for one week: a workout type, 'RECOVERY', or None (rest day)."""
    days = ctx["days"]
    kinds = list(TEMPLATES[ctx["group"]][5 if days == 7 else days])
    if not ctx["split_ok"]:
        kinds = [SIMPLER.get(k, k) for k in kinds]
    if days == 6 and ctx["level"] <= 1:
        kinds[-1] = "RECOVERY"       # beginners: one of the 6 days is an easy session
    week = [None] * 7
    for position, kind in zip(WEEK_LAYOUT[days], kinds):
        week[position] = kind
    if days == 7:                    # every day active, but two are light recovery sessions
        week[3] = "RECOVERY"
        week[6] = "RECOVERY"
    return week


# ---------- picking and fitting one workout ----------
def usable_exercises(program, ctx):
    """The exercises of a workout this user can do (equipment, level, movements to avoid)."""
    names = []
    for ex in program["exercises"]:
        info = EXERCISE_INFO[ex["name"]]
        if info["equip"] not in ctx["tokens"] or info["level"] > ctx["level"]:
            continue
        if ctx["mode"] == "avoid" and info["avoid"] & ctx["areas"]:
            continue
        names.append(ex["name"])
    return names


def is_light(name, ctx):
    return ctx["mode"] == "light" and bool(EXERCISE_INFO[name]["avoid"] & ctx["areas"])


def session_seconds(program, names, adjust, ctx):
    by_name = {ex["name"]: ex for ex in program["exercises"]}
    return sum(
        exercise_seconds(by_name[n], day_sets(by_name[n]["sets"], adjust, ctx["cap"], is_light(n, ctx)))
        for n in names
    )


def candidate_programs(kind, ctx):
    """Workouts of this type that fit the user's equipment and level, best first."""
    options = []
    for program in ALL_PROGRAMS:
        meta = PROGRAM_META[program["name"]]
        if meta["kind"] != kind or meta["min_level"] > ctx["level"]:
            continue
        if not program_requires(program) <= ctx["tokens"]:
            continue
        if len(usable_exercises(program, ctx)) < MIN_EXERCISES:
            continue
        options.append(program)
    is_existing = {w["name"] for w in WORKOUTS}

    def long_enough(program):
        """Can this workout reach (about) the chosen minimum, even with extra sets?"""
        longest = session_seconds(program, usable_exercises(program, ctx), MAX_EXTRA_SETS, ctx)
        return longest >= ctx["low"] * 60 * 0.9

    options.sort(key=lambda p: (not long_enough(p), ctx["rank"][program_tier(p)], p["name"] not in is_existing, p["name"]))
    return options


def fit_to_duration(program, ctx):
    """Trim or extend one workout to the chosen duration.
    Returns (exercise names, set_adjust). Too long: fewer sets, then fewer exercises.
    Too short: more sets (up to +2 per exercise)."""
    names = usable_exercises(program, ctx)
    adjust = ctx["base_adjust"]
    limit, target = ctx["high"] * 60, ctx["low"] * 60
    while session_seconds(program, names, adjust, ctx) > limit:
        if adjust > -2:
            adjust -= 1
        elif len(names) > MIN_EXERCISES:
            names = names[:-1]          # programs list the most important exercises first
        else:
            break
    while session_seconds(program, names, adjust, ctx) < target and adjust < MAX_EXTRA_SETS:
        longer = session_seconds(program, names, adjust + 1, ctx)
        if longer > limit or longer == session_seconds(program, names, adjust, ctx):
            break
        adjust += 1
    return names, adjust


def build_day(day, kind, variant, ctx):
    """One plan day (a workout, a recovery session or a rest day)."""
    week = (day - 1) // 7 + 1
    rest = {
        "day": day, "week": week, "type": "rest", "title": "Rest Day", "workout": None,
        "exercises": [], "exercise_count": 0, "max_sets": 0, "set_adjust": 0, "light": [],
        "duration_min": 0, "focus": "Recovery",
    }
    if kind is None:
        return rest

    if kind == "RECOVERY":
        program = find_workout("Active Recovery")
        names = usable_exercises(program, ctx)
        if len(names) < 2:
            return rest
        entry_type, adjust, title, focus = "recovery", 0, KIND_TITLE["RECOVERY"], "Recovery"
        options = [program]
    else:
        options = candidate_programs(kind, ctx)
        if not options and kind != "FULL":
            options = candidate_programs("FULL", ctx)
        if not options:   # very unusual: lots of movements avoided. Use the best partial match.
            allowed = [p for p in ALL_PROGRAMS
                       if program_requires(p) <= ctx["tokens"] and PROGRAM_META[p["name"]]["kind"] != "RECOVERY"]
            options = sorted(allowed, key=lambda p: (-len(usable_exercises(p, ctx)), p["name"]))[:3]
            if not options or not usable_exercises(options[0], ctx):
                return rest
        top = options[:2]                     # alternate between the two best choices
        first = top[variant % len(top)]
        options = [first] + [p for p in options if p is not first]
        entry_type, title = "workout", KIND_TITLE.get(kind, "Full Body")
        focus = "Conditioning" if kind == "CORE" else ctx["focus"]

    for program in options:
        if entry_type == "recovery":
            names, adjust = usable_exercises(program, ctx), 0
        else:
            names, adjust = fit_to_duration(program, ctx)
        if names:
            break
    seconds = session_seconds(program, names, adjust, ctx)
    return {
        "day": day, "week": week, "type": entry_type, "title": title, "workout": program["name"],
        "exercises": names, "exercise_count": len(names), "max_sets": ctx["cap"],
        "set_adjust": adjust, "light": [n for n in names if is_light(n, ctx)],
        "duration_min": max(5, round(seconds / 60)), "focus": focus,
    }


def generate_plan(answers):
    """Build the full 30-day plan (a list of 30 day dictionaries) from the onboarding answers.

    answers = {"goal", "level", "location", "equipment", "days", "duration", "movement"}"""
    ctx = plan_context(answers)
    week = week_kinds(ctx)
    plan = []
    for day in range(1, PLAN_LENGTH + 1):
        kind = week[(day - 1) % 7]
        week_number = (day - 1) // 7
        first_of_week = day - ((day - 1) % 7)
        in_week = sum(1 for d in range(first_of_week, day) if week[(d - 1) % 7] == kind)
        # the same workout repeats for two weeks, then switches to the other choice
        variant = in_week + week_number // 2
        plan.append(build_day(day, kind, variant, ctx))
    return plan


def plan_day_workout(entry):
    """Turn a plan day back into a normal workout dictionary (None for a rest day).
    The result works with the existing workout detail screen and workout player."""
    base = find_workout(entry.get("workout")) if entry.get("workout") else None
    if base is None or entry.get("type") == "rest":
        return None
    by_name = {ex["name"]: ex for ex in base["exercises"]}
    light = set(entry.get("light") or [])
    exercises = []
    for name in entry["exercises"]:
        source = by_name.get(name)
        if source is not None:
            sets = day_sets(source["sets"], entry.get("set_adjust", 0), entry.get("max_sets", 6), name in light)
            exercises.append({**source, "sets": sets})
    return {
        "name": entry["title"],
        "description": f"{base['name']}  •  Day {entry['day']} of {PLAN_LENGTH}",
        "duration": f"{entry['duration_min']} min",
        "level": base["level"],
        "icon": base["icon"],
        "exercises": exercises,
        "program_day": entry["day"],
    }


# ---------------------------------------------------------------
# 3. SAVED USER DATA (stored in a small local file)
# ---------------------------------------------------------------
def data_file_path() -> Path:
    """Where we save the data. On a phone Flet gives us a private folder."""
    folder = os.getenv("FLET_APP_STORAGE_DATA") or str(Path(__file__).resolve().parent)
    return Path(folder) / "fitlife_data.json"


def default_data() -> dict:
    """Starting data for a new user. Dates are relative to today."""

    def days_ago(n):
        return (date.today() - timedelta(days=n)).isoformat()

    return {
        "profile": {
            "name": "Alex Johnson",
            "height_cm": 178,
            "age": 28,
            "level": "Beginner",
            "goal_kg": 75.0,
        },
        "settings": {"units": "kg", "notifications": True},
        "weights": [
            {"date": days_ago(35), "kg": 90.0},
            {"date": days_ago(28), "kg": 88.5},
            {"date": days_ago(21), "kg": 86.5},
            {"date": days_ago(14), "kg": 85.0},
            {"date": days_ago(7), "kg": 83.5},
            {"date": days_ago(1), "kg": 82.0},
        ],
        # Newest first.
        "history": [
            {"date": days_ago(1), "name": "Full Body", "seconds": 2160, "sets": 18},
            {"date": days_ago(3), "name": "Leg Day", "seconds": 2640, "sets": 20},
            {"date": days_ago(5), "name": "Pull Day", "seconds": 2340, "sets": 23},
            {"date": days_ago(6), "name": "Push Day", "seconds": 2460, "sets": 22},
        ],
        # ----- Onboarding answers (filled in the first time you open FitLife) -----
        "sample_data": True,               # True = the demo numbers above (cleared by onboarding)
        "onboarding_completed": False,
        "fitness_goal": "",
        "experience_level": "",
        "training_location": "",
        "equipment": [],                   # e.g. ["Dumbbells", "Resistance bands"]
        "training_days_per_week": 0,
        "workout_duration": "",
        "movement_considerations": {"mode": "none", "areas": []},   # "none", "avoid" or "light"
        # ----- The personalized 30-day plan (created when onboarding is finished) -----
        "thirty_day_plan": [],             # exactly 30 day dictionaries once created
        "program_start_date": None,        # the date Day 1 started, e.g. "2026-10-01"
        "current_program_day": 1,
        "completed_program_days": [],      # e.g. [1, 3, 4] (filled in by a later step)
    }


DATA = default_data()


def load_data():
    """Read the saved file (if it exists) into DATA."""
    try:
        saved = json.loads(data_file_path().read_text(encoding="utf-8"))
        fresh = default_data()
        for key in fresh:
            if key in saved:
                if isinstance(fresh[key], dict):
                    fresh[key].update(saved[key])
                else:
                    fresh[key] = saved[key]
        # An older save file (from before onboarding) has real numbers: keep them.
        if "sample_data" not in saved:
            fresh["sample_data"] = False
        if not isinstance(fresh["equipment"], list):
            fresh["equipment"] = []
        if not isinstance(fresh["thirty_day_plan"], list):
            fresh["thirty_day_plan"] = []
        if not isinstance(fresh["completed_program_days"], list):
            fresh["completed_program_days"] = []
        try:
            fresh["training_days_per_week"] = int(fresh["training_days_per_week"] or 0)
        except (TypeError, ValueError):
            fresh["training_days_per_week"] = 0
        DATA.clear()
        DATA.update(fresh)
    except Exception:
        pass  # No file yet, or it's damaged: just use the starting data.


def save_data():
    """Write DATA to the file. Never crashes the app if saving fails."""
    try:
        data_file_path().write_text(json.dumps(DATA, indent=2), encoding="utf-8")
    except Exception as error:
        print("Could not save data:", error)


# ---------------------------------------------------------------
# 4. HELPER FUNCTIONS
# ---------------------------------------------------------------
def format_time(total_seconds: int) -> str:
    """Turn 75 seconds into '01:15'."""
    minutes, seconds = divmod(max(0, int(total_seconds)), 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_duration(total_seconds: int) -> str:
    """Turn 7800 seconds into '2h 10m'."""
    hours, minutes = divmod(int(total_seconds) // 60, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def friendly_date(iso: str) -> str:
    """Turn '2026-09-28' into 'Yesterday', '3 days ago' or '12 Sep'."""
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return iso
    diff = (date.today() - day).days
    if diff == 0:
        return "Today"
    if diff == 1:
        return "Yesterday"
    if 1 < diff < 7:
        return f"{diff} days ago"
    return f"{day.day} {day.strftime('%b')}"


def get_workout(name: str) -> dict:
    """Find a workout in WORKOUTS by its name."""
    for workout in WORKOUTS:
        if workout["name"] == name:
            return workout
    return WORKOUTS[0]


def suggested_workout() -> dict:
    """Today's workout = the next program after the last one you did."""
    names = [w["name"] for w in WORKOUTS]
    if DATA["history"] and DATA["history"][0]["name"] in names:
        last = names.index(DATA["history"][0]["name"])
        return WORKOUTS[(last + 1) % len(WORKOUTS)]
    return WORKOUTS[0]


def units() -> str:
    return DATA["settings"]["units"]


def to_display(kg: float) -> float:
    """Convert kg to the unit the user chose."""
    return kg * KG_TO_LB if units() == "lb" else kg


def from_display(value: float) -> float:
    """Convert a number in the user's unit back to kg (how we store it)."""
    return value / KG_TO_LB if units() == "lb" else value


def fmt_weight(kg: float) -> str:
    return f"{to_display(kg):.1f} {units()}"


def parse_number(text):
    """Turn typed text into a number, or None if it isn't one."""
    try:
        return float(str(text).strip().replace(",", "."))
    except ValueError:
        return None


def workout_days() -> set:
    return {date.fromisoformat(h["date"]) for h in DATA["history"]}


def current_streak() -> int:
    """How many days in a row you trained (counting back from today)."""
    days = workout_days()
    day = date.today()
    if day not in days:
        day -= timedelta(days=1)  # it's fine if you haven't trained yet today
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def this_week_history() -> list:
    monday = date.today() - timedelta(days=date.today().weekday())
    return [h for h in DATA["history"] if date.fromisoformat(h["date"]) >= monday]


def week_activity() -> list:
    """(letter, trained?, is_today) for Monday to Sunday of this week."""
    days = workout_days()
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = []
    for i, letter in enumerate("MTWTFSS"):
        day = monday + timedelta(days=i)
        result.append((letter, day in days, day == today))
    return result


def greeting_text() -> str:
    hour = time.localtime().tm_hour
    if hour < 12:
        return "Good morning 👋"
    if hour < 18:
        return "Good afternoon 👋"
    return "Good evening 👋"


def goal_label() -> str:
    current = DATA["weights"][-1]["kg"]
    goal = DATA["profile"]["goal_kg"]
    if goal < current - 0.05:
        return "Goal: Lose weight"
    if goal > current + 0.05:
        return "Goal: Gain weight"
    return "Goal: Maintain weight"


def weight_progress() -> float:
    """Progress from start weight to goal weight, between 0.0 and 1.0."""
    start = DATA["weights"][0]["kg"]
    current = DATA["weights"][-1]["kg"]
    goal = DATA["profile"]["goal_kg"]
    total = abs(start - goal)
    if total < 0.05:
        return 1.0
    done = (start - current) if goal < start else (current - start)
    return max(0.0, min(1.0, done / total))


# ---------------------------------------------------------------
# 4b. ONBOARDING (questions + saving the answers)
# ---------------------------------------------------------------
# The order of the questions, one per screen.
ONBOARDING_STEPS = [
    "goal", "level", "location", "equipment", "days", "duration",
    "height", "weight", "age", "goal_weight",
]

# (label, small description, icon) for every choice
GOAL_CHOICES = [
    ("Lose weight", "Burn fat and feel lighter", ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED),
    ("Build muscle", "Get bigger and more defined", ft.Icons.FITNESS_CENTER),
    ("Get stronger", "Lift more over time", ft.Icons.BOLT),
    ("Improve fitness", "More energy and stamina", ft.Icons.DIRECTIONS_RUN),
    ("Build a healthy routine", "Make training a habit", ft.Icons.EVENT_REPEAT),
    ("Maintain weight", "Stay where you are and keep fit", ft.Icons.BALANCE),
]
LEVEL_CHOICES = [
    ("Complete beginner", "I have never really trained", ft.Icons.EMOJI_PEOPLE),
    ("Beginner", "Some experience, less than a year", ft.Icons.TRENDING_UP),
    ("Intermediate", "Training regularly for 1 to 3 years", ft.Icons.SHOW_CHART),
    ("Advanced", "Training consistently for 3+ years", ft.Icons.MILITARY_TECH),
]
LOCATION_CHOICES = [
    ("Home", "I train at home", ft.Icons.HOME_OUTLINED),
    ("Gym", "I train at a gym", ft.Icons.FITNESS_CENTER),
    ("Both", "A mix of home and gym", ft.Icons.SWAP_HORIZ),
]
EQUIPMENT_CHOICES = [
    ("No equipment", "Bodyweight only", ft.Icons.ACCESSIBILITY_NEW),
    ("Dumbbells", "Any set of dumbbells", ft.Icons.FITNESS_CENTER),
    ("Resistance bands", "Loop or tube bands", ft.Icons.LINEAR_SCALE),
    ("Barbell", "A barbell with a bench or rack", ft.Icons.HORIZONTAL_RULE),
    ("Full gym", "Machines, cables and free weights", ft.Icons.STORE),
]
DAY_OPTIONS = [2, 3, 4, 5, 6, 7]
DURATION_CHOICES = [
    ("15–20 minutes", "Quick and efficient", ft.Icons.TIMER_OUTLINED),
    ("20–30 minutes", "A short session", ft.Icons.TIMER_OUTLINED),
    ("30–45 minutes", "A solid workout", ft.Icons.TIMER_OUTLINED),
    ("45–60 minutes", "A full session", ft.Icons.TIMER_OUTLINED),
    ("60+ minutes", "Long sessions", ft.Icons.TIMER_OUTLINED),
]

# The profile only has 3 levels, so "Complete beginner" shows as "Beginner" there.
LEVEL_TO_PROFILE = {
    "Complete beginner": "Beginner",
    "Beginner": "Beginner",
    "Intermediate": "Intermediate",
    "Advanced": "Advanced",
}


def onboarding_defaults() -> dict:
    """The starting answers. New users start empty; existing users see their own numbers."""
    profile = DATA["profile"]
    fresh = DATA.get("sample_data", False)  # True = still the demo data
    latest = DATA["weights"][-1]["kg"] if DATA["weights"] else None
    return {
        "goal": DATA.get("fitness_goal") or None,
        "level": DATA.get("experience_level") or None,
        "location": DATA.get("training_location") or None,
        "equipment": list(DATA.get("equipment") or []),
        "days": DATA.get("training_days_per_week") or None,
        "duration": DATA.get("workout_duration") or None,
        "height": "" if fresh else str(profile["height_cm"]),
        "weight": "" if (fresh or latest is None) else f"{to_display(latest):.1f}",
        "age": "" if fresh else str(profile["age"]),
        "goal_weight": "" if fresh else f"{to_display(profile['goal_kg']):.1f}",
    }


def apply_onboarding(ans: dict):
    """Save the onboarding answers into DATA and into fitlife_data.json."""
    profile = DATA["profile"]
    if DATA.get("sample_data"):
        # First launch: remove the demo weights and workouts so your data starts clean.
        DATA["weights"] = []
        DATA["history"] = []
        DATA["sample_data"] = False
        profile["name"] = "Athlete"  # you can change this in Profile > Edit Profile

    # Height, age and goal weight live in the existing profile.
    profile["height_cm"] = int(round(parse_number(ans["height"])))
    profile["age"] = int(round(parse_number(ans["age"])))
    profile["goal_kg"] = round(from_display(parse_number(ans["goal_weight"])), 2)
    profile["level"] = LEVEL_TO_PROFILE.get(ans["level"], "Beginner")

    # Current weight becomes today's weigh-in (same list the Progress screen uses).
    today = date.today().isoformat()
    DATA["weights"] = [w for w in DATA["weights"] if w["date"] != today]
    DATA["weights"].append({"date": today, "kg": round(from_display(parse_number(ans["weight"])), 2)})
    DATA["weights"].sort(key=lambda w: w["date"])

    DATA["fitness_goal"] = ans["goal"]
    DATA["experience_level"] = ans["level"]
    DATA["training_location"] = ans["location"]
    DATA["equipment"] = list(ans["equipment"])
    DATA["training_days_per_week"] = int(ans["days"])
    DATA["workout_duration"] = ans["duration"]
    DATA["onboarding_completed"] = True
    create_plan()  # builds the 30-day plan, starts it today and saves everything


# ---------------------------------------------------------------
# 4c. THE SAVED 30-DAY PLAN (create it once, keep it until reset)
# ---------------------------------------------------------------
def plan_answers_from_data() -> dict:
    """The onboarding answers, in the form the plan generator wants."""
    return {
        "goal": DATA.get("fitness_goal"),
        "level": DATA.get("experience_level"),
        "location": DATA.get("training_location"),
        "equipment": list(DATA.get("equipment") or []),
        "days": DATA.get("training_days_per_week"),
        "duration": DATA.get("workout_duration"),
        "movement": DATA.get("movement_considerations"),
    }


def plan_is_valid(plan) -> bool:
    """True if this is a complete plan: Day 1 to Day 30, pointing at real workouts."""
    if not isinstance(plan, list) or len(plan) != PLAN_LENGTH:
        return False
    for number, entry in enumerate(plan, start=1):
        if not isinstance(entry, dict) or entry.get("day") != number:
            return False
        if entry.get("type") == "rest":
            continue
        if entry.get("type") not in ("workout", "recovery"):
            return False
        program = find_workout(entry.get("workout"))
        names = entry.get("exercises")
        if program is None or not isinstance(names, list) or not names:
            return False
        if any(n not in {ex["name"] for ex in program["exercises"]} for n in names):
            return False
    return True


def valid_start_date(value) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def create_plan():
    """Make a brand-new 30-day plan that starts today, and save it."""
    DATA["thirty_day_plan"] = generate_plan(plan_answers_from_data())
    DATA["program_start_date"] = date.today().isoformat()
    DATA["current_program_day"] = 1
    DATA["completed_program_days"] = []
    save_data()


def ensure_plan():
    """Called when the app starts. A good saved plan is left alone (never regenerated).
    A missing plan is created; a damaged one is rebuilt (your start date and progress are kept)."""
    if not DATA.get("onboarding_completed"):
        return
    plan_ok = plan_is_valid(DATA.get("thirty_day_plan"))
    start_ok = valid_start_date(DATA.get("program_start_date"))
    if plan_ok and start_ok:
        return
    if not plan_ok and not start_ok:
        create_plan()                      # nothing saved yet: Day 1 is today
        return
    if plan_ok:                            # plan fine, start date missing or broken
        DATA["program_start_date"] = date.today().isoformat()
        DATA["current_program_day"] = 1
    else:                                  # start date fine, plan damaged
        DATA["thirty_day_plan"] = generate_plan(plan_answers_from_data())
    save_data()


def format_plan_summary() -> str:
    """A plain-text list of the saved plan (printed in the terminal when the app starts)."""
    plan = DATA.get("thirty_day_plan") or []
    if not plan:
        return "FitLife: no 30-day plan yet (finish onboarding first)."
    lines = [
        f"FitLife 30-day plan | starts {DATA.get('program_start_date')} | {DATA.get('fitness_goal')}, "
        f"{DATA.get('experience_level')}, {DATA.get('training_days_per_week')} days/week, "
        f"{DATA.get('workout_duration')}"
    ]
    for d in plan:
        if d["type"] == "rest":
            lines.append(f"  Day {d['day']:>2}: REST")
        else:
            lines.append(
                f"  Day {d['day']:>2}: {d['title']:<16} {d['duration_min']:>3} min  "
                f"{d['exercise_count']} exercises  [{d['workout']}]"
            )
    rest_days = sum(1 for d in plan if d["type"] == "rest")
    lines.append(f"  Total: {len(plan)} days, {len(plan) - rest_days} active days, {rest_days} rest days")
    return "\n".join(lines)


class Actions:
    """A bundle of functions screens can call. main() fills these in."""

    def __init__(self):
        self.go_tab = lambda index: None
        self.open_workout = lambda workout: None
        self.refresh = lambda: None
        self.start_app = lambda: None
        self.open_plan = lambda: None
        self.open_plan_workout = lambda workout: None
        self.open_fitness_plan = lambda: None


# ---------------------------------------------------------------
# 5. SMALL REUSABLE UI PIECES
# ---------------------------------------------------------------
def stat_tile(icon, label, value, on_click=None):
    """One small stat box (icon, big value, small label)."""
    return ft.Container(
        expand=True,
        bgcolor=CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(14),
        ink=on_click is not None,
        on_click=on_click,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Icon(icon, color=ACCENT, size=24),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Text(label, size=12, color=TEXT_MUTED),
            ],
        ),
    )


def info_chip(icon, text):
    """Small pill with an icon."""
    return ft.Container(
        bgcolor=CARD_LIGHT,
        border_radius=30,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                ft.Icon(icon, size=16, color=ACCENT),
                ft.Text(text, size=13, color=TEXT_PRIMARY),
            ],
        ),
    )


def pill_button(icon, text, on_click):
    """A tappable pill (like info_chip, but you can press it)."""
    return ft.Container(
        bgcolor=CARD_LIGHT,
        border_radius=30,
        ink=True,
        on_click=on_click,
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                ft.Icon(icon, size=18, color=ACCENT),
                ft.Text(text, size=14, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
            ],
        ),
    )


def screen_title(title: str, subtitle: str):
    """Big title with a small line underneath."""
    return ft.Column(
        spacing=2,
        controls=[
            ft.Text(title, size=30, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text(subtitle, size=15, color=TEXT_MUTED),
        ],
    )


def section_title(text: str):
    return ft.Text(text, size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)


def primary_button(label: str, on_click, icon=ft.Icons.PLAY_ARROW_ROUNDED):
    """The big lime button."""
    return ft.Container(
        height=60,
        bgcolor=ACCENT,
        border_radius=18,
        ink=True,
        on_click=on_click,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Icon(icon, color=BG_COLOR, size=28),
                ft.Text(label, size=18, weight=ft.FontWeight.BOLD, color=BG_COLOR),
            ],
        ),
    )


def secondary_button(label: str, on_click, icon=None):
    """A darker button for less important actions."""
    controls = []
    if icon is not None:
        controls.append(ft.Icon(icon, color=TEXT_PRIMARY, size=22))
    controls.append(ft.Text(label, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY))
    return ft.Container(
        height=60,
        bgcolor=CARD_LIGHT,
        border_radius=18,
        ink=True,
        on_click=on_click,
        content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=8, controls=controls),
    )


def workout_list_item(workout: dict, on_open):
    """One tappable workout card for the Workouts list."""
    count = len(workout["exercises"])
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(16),
        ink=True,
        on_click=lambda e: on_open(workout),
        content=ft.Row(
            spacing=16,
            controls=[
                ft.Container(
                    width=56,
                    height=56,
                    bgcolor=CARD_LIGHT,
                    border_radius=18,
                    content=ft.Icon(workout["icon"], color=ACCENT, size=28),
                ),
                ft.Column(
                    expand=True,
                    spacing=4,
                    controls=[
                        ft.Text(workout["name"], size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(workout["description"], size=13, color=TEXT_MUTED),
                        ft.Text(
                            f"{workout['duration']}  •  {count} exercises  •  {workout['level']}",
                            size=12,
                            color=ACCENT,
                        ),
                    ],
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_MUTED, size=24),
            ],
        ),
    )


def exercise_item(number: int, ex: dict, on_tap):
    """One numbered, tappable exercise row on the workout detail screen."""
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(14),
        ink=True,
        on_click=lambda e: on_tap(ex),
        content=ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=20,
                    bgcolor=CARD_LIGHT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(str(number), size=16, weight=ft.FontWeight.BOLD, color=ACCENT),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(ex["name"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(ex["muscle"], size=12, color=TEXT_MUTED),
                    ],
                ),
                ft.Column(
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    controls=[
                        ft.Text(
                            f"{ex['sets']} × {ex['reps']}",
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ACCENT,
                        ),
                        ft.Text(f"Rest {ex['rest']}s", size=12, color=TEXT_MUTED),
                    ],
                ),
            ],
        ),
    )


def library_item(ex: dict, on_tap):
    """One row in the Exercise Library."""
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(14),
        ink=True,
        on_click=lambda e: on_tap(ex),
        content=ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    width=44,
                    height=44,
                    bgcolor=CARD_LIGHT,
                    border_radius=14,
                    content=ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, color=ACCENT, size=24),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(ex["name"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(ex["muscle"], size=12, color=TEXT_MUTED),
                    ],
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_MUTED, size=22),
            ],
        ),
    )


def weight_bar_chart():
    """A simple bar chart of your last 6 weigh-ins (made from containers)."""
    entries = DATA["weights"][-6:]
    values = [to_display(w["kg"]) for w in entries]
    low, high = min(values), max(values)
    span = max(high - low, 1)

    bars = []
    for i, (entry, value) in enumerate(zip(entries, values)):
        is_latest = i == len(entries) - 1
        day = date.fromisoformat(entry["date"])
        bar_height = 40 + ((value - low) / span) * 80  # between 40 and 120 px
        bars.append(
            ft.Column(
                expand=True,
                height=180,
                spacing=6,
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(f"{value:.1f}", size=11, color=ACCENT if is_latest else TEXT_MUTED),
                    ft.Container(
                        width=26,
                        height=bar_height,
                        border_radius=8,
                        bgcolor=ACCENT if is_latest else CARD_LIGHT,
                    ),
                    ft.Text(f"{day.day} {day.strftime('%b')}", size=10, color=TEXT_MUTED),
                ],
            )
        )
    return ft.Row(spacing=4, controls=bars)


def week_row():
    """Seven circles showing which days you trained this week."""
    days = []
    for letter, done, is_today in week_activity():
        days.append(
            ft.Column(
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=36,
                        height=36,
                        border_radius=18,
                        bgcolor=ACCENT if done else CARD_LIGHT,
                        border=ft.Border.all(1.5, TEXT_MUTED) if (is_today and not done) else None,
                        content=ft.Icon(
                            ft.Icons.CHECK if done else ft.Icons.REMOVE,
                            size=18,
                            color=BG_COLOR if done else TEXT_MUTED,
                        ),
                    ),
                    ft.Text(
                        letter,
                        size=12,
                        color=TEXT_PRIMARY if is_today else TEXT_MUTED,
                        weight=ft.FontWeight.BOLD if is_today else ft.FontWeight.NORMAL,
                    ),
                ],
            )
        )
    return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=days)


def history_item(item: dict, on_tap):
    """One tappable row in the 'Recent workouts' list."""
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(14),
        ink=True,
        on_click=lambda e: on_tap(item),
        content=ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    width=44,
                    height=44,
                    bgcolor=CARD_LIGHT,
                    border_radius=14,
                    content=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ACCENT, size=24),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(item["name"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(friendly_date(item["date"]), size=12, color=TEXT_MUTED),
                    ],
                ),
                ft.Text(format_duration(item["seconds"]), size=14, color=ACCENT),
            ],
        ),
    )


def settings_row(icon, label: str, on_click=None, trailing=None):
    """One row in the Profile settings list."""
    controls = [
        ft.Icon(icon, color=ACCENT, size=22),
        ft.Text(label, size=16, color=TEXT_PRIMARY, expand=True),
    ]
    controls.append(trailing if trailing is not None else ft.Icon(ft.Icons.CHEVRON_RIGHT, color=TEXT_MUTED, size=22))
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        ink=on_click is not None,
        on_click=on_click,
        content=ft.Row(spacing=14, controls=controls),
    )


# ---------------------------------------------------------------
# 6. POPUPS (dialogs and bottom sheets)
# ---------------------------------------------------------------
def toast(page: ft.Page, text: str):
    """A small message at the bottom of the screen."""
    page.show_dialog(ft.SnackBar(content=ft.Text(text)))


def styled_field(**kwargs) -> ft.TextField:
    """A text box that matches our dark theme."""
    return ft.TextField(
        border_color=CARD_LIGHT,
        focused_border_color=ACCENT,
        color=TEXT_PRIMARY,
        cursor_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_MUTED),
        **kwargs,
    )


def dialog_button(text: str, on_click, color=ACCENT):
    return ft.TextButton(text, on_click=on_click, style=ft.ButtonStyle(color=color))


def show_message_dialog(page: ft.Page, title: str, message: str):
    page.show_dialog(
        ft.AlertDialog(
            bgcolor=CARD_COLOR,
            title=ft.Text(title, color=TEXT_PRIMARY),
            content=ft.Text(message, color=TEXT_MUTED),
            actions=[dialog_button("OK", lambda e: page.pop_dialog())],
        )
    )


def show_log_weight_dialog(page: ft.Page, on_saved):
    """Popup to record today's weight."""
    latest = DATA["weights"][-1]["kg"]
    field = styled_field(
        value=f"{to_display(latest):.1f}",
        label=f"Weight ({units()})",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )
    low, high = (30, 300) if units() == "kg" else (66, 660)

    def save(e):
        value = parse_number(field.value)
        if value is None or not (low <= value <= high):
            field.error = f"Enter a weight between {low} and {high} {units()}"
            field.update()
            return
        today = date.today().isoformat()
        DATA["weights"] = [w for w in DATA["weights"] if w["date"] != today]
        DATA["weights"].append({"date": today, "kg": round(from_display(value), 2)})
        DATA["weights"].sort(key=lambda w: w["date"])
        save_data()
        page.pop_dialog()
        on_saved()
        toast(page, "Weight saved ✅")

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            bgcolor=CARD_COLOR,
            title=ft.Text("Log today's weight", color=TEXT_PRIMARY),
            content=ft.Container(width=280, content=field),
            actions=[
                dialog_button("Cancel", lambda e: page.pop_dialog(), color=TEXT_MUTED),
                dialog_button("Save", save),
            ],
        )
    )


def show_edit_profile_dialog(page: ft.Page, on_saved):
    """Popup to edit your name, height, age, goal weight and level."""
    profile = DATA["profile"]
    name_field = styled_field(value=profile["name"], label="Name")
    height_field = styled_field(
        value=str(profile["height_cm"]), label="Height (cm)", keyboard_type=ft.KeyboardType.NUMBER
    )
    age_field = styled_field(
        value=str(profile["age"]), label="Age", keyboard_type=ft.KeyboardType.NUMBER
    )
    goal_field = styled_field(
        value=f"{to_display(profile['goal_kg']):.1f}",
        label=f"Goal weight ({units()})",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    level_dropdown = ft.Dropdown(
        value=profile["level"],
        label="Level",
        border_color=CARD_LIGHT,
        focused_border_color=ACCENT,
        color=TEXT_PRIMARY,
        bgcolor=CARD_LIGHT,
        options=[ft.DropdownOption(key=lvl, text=lvl) for lvl in ("Beginner", "Intermediate", "Advanced")],
    )

    def save(e):
        problems = False
        name = (name_field.value or "").strip()
        height = parse_number(height_field.value)
        age = parse_number(age_field.value)
        goal = parse_number(goal_field.value)
        low, high = (30, 300) if units() == "kg" else (66, 660)

        name_field.error = None if name else "Please enter your name"
        height_field.error = None if height and 100 <= height <= 250 else "Between 100 and 250"
        age_field.error = None if age and 10 <= age <= 100 else "Between 10 and 100"
        goal_field.error = None if goal and low <= goal <= high else f"Between {low} and {high}"
        for field in (name_field, height_field, age_field, goal_field):
            if field.error:
                problems = True
            field.update()
        if problems:
            return

        profile["name"] = name
        profile["height_cm"] = int(height)
        profile["age"] = int(age)
        profile["goal_kg"] = round(from_display(goal), 2)
        profile["level"] = level_dropdown.value or "Beginner"
        save_data()
        page.pop_dialog()
        on_saved()
        toast(page, "Profile updated ✅")

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            bgcolor=CARD_COLOR,
            title=ft.Text("Edit profile", color=TEXT_PRIMARY),
            content=ft.Container(
                width=300,
                content=ft.Column(
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=14,
                    controls=[name_field, height_field, age_field, goal_field, level_dropdown],
                ),
            ),
            actions=[
                dialog_button("Cancel", lambda e: page.pop_dialog(), color=TEXT_MUTED),
                dialog_button("Save", save),
            ],
        )
    )


def show_reset_dialog(page: ft.Page, on_reset):
    """Ask before erasing all data."""

    def do_reset(e):
        DATA.clear()
        DATA.update(default_data())
        save_data()
        page.pop_dialog()
        on_reset()
        toast(page, "All data was reset")

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            bgcolor=CARD_COLOR,
            title=ft.Text("Reset all data?", color=TEXT_PRIMARY),
            content=ft.Text(
                "This removes your weights, workout history and profile changes. You will set up FitLife again.",
                color=TEXT_MUTED,
            ),
            actions=[
                dialog_button("Cancel", lambda e: page.pop_dialog(), color=TEXT_MUTED),
                dialog_button("Reset", do_reset, color=DANGER),
            ],
        )
    )


def show_exercise_sheet(page: ft.Page, ex: dict):
    """Bottom sheet with instructions for one exercise."""
    steps, tip = INSTRUCTIONS.get(ex["name"], DEFAULT_INSTRUCTIONS)

    step_rows = []
    for i, step in enumerate(steps):
        step_rows.append(
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=12,
                controls=[
                    ft.Container(
                        width=28,
                        height=28,
                        border_radius=14,
                        bgcolor=CARD_LIGHT,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(str(i + 1), size=13, weight=ft.FontWeight.BOLD, color=ACCENT),
                    ),
                    ft.Text(step, size=15, color=TEXT_PRIMARY, expand=True),
                ],
            )
        )

    page.show_dialog(
        ft.BottomSheet(
            bgcolor=CARD_COLOR,
            show_drag_handle=True,
            scrollable=True,
            content=ft.Container(
                padding=ft.Padding.only(left=20, right=20, bottom=24),
                content=ft.Column(
                    tight=True,
                    spacing=16,
                    controls=[
                        ft.Text(ex["name"], size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        info_chip(ft.Icons.FITNESS_CENTER, ex["muscle"]),
                        ft.Container(
                            height=130,
                            bgcolor=CARD_LIGHT,
                            border_radius=20,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, size=44, color=ACCENT),
                                    ft.Text("Demo video coming soon", size=12, color=TEXT_MUTED),
                                ],
                            ),
                        ),
                        section_title("How to do it"),
                        *step_rows,
                        ft.Container(
                            bgcolor=CARD_LIGHT,
                            border_radius=16,
                            padding=ft.Padding.all(14),
                            content=ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                spacing=10,
                                controls=[
                                    ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=ACCENT, size=20),
                                    ft.Text(tip, size=14, color=TEXT_PRIMARY, expand=True),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )
    )


def show_history_sheet(page: ft.Page, item: dict):
    """Bottom sheet with the details of one finished workout."""
    page.show_dialog(
        ft.BottomSheet(
            bgcolor=CARD_COLOR,
            show_drag_handle=True,
            content=ft.Container(
                padding=ft.Padding.only(left=20, right=20, bottom=24),
                content=ft.Column(
                    tight=True,
                    spacing=16,
                    controls=[
                        ft.Text(item["name"], size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(friendly_date(item["date"]), size=14, color=TEXT_MUTED),
                        ft.Row(
                            spacing=12,
                            controls=[
                                stat_tile(ft.Icons.TIMER_OUTLINED, "Time", format_duration(item["seconds"])),
                                stat_tile(ft.Icons.REPEAT_ROUNDED, "Sets", str(item.get("sets", "-"))),
                            ],
                        ),
                    ],
                ),
            ),
        )
    )


# ---------------------------------------------------------------
# 7. SCREENS (one function per screen)
# ---------------------------------------------------------------
def option_card(label, subtitle, icon, selected, on_click):
    """A large selectable card used in onboarding."""
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(16),
        ink=True,
        border=ft.Border.all(2, ACCENT if selected else CARD_LIGHT),
        on_click=on_click,
        content=ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    width=48,
                    height=48,
                    border_radius=16,
                    bgcolor=ACCENT if selected else CARD_LIGHT,
                    content=ft.Icon(icon, color=BG_COLOR if selected else ACCENT, size=26),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(label, size=17, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(subtitle, size=13, color=TEXT_MUTED),
                    ],
                ),
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=ACCENT if selected else TEXT_MUTED,
                    size=24,
                ),
            ],
        ),
    )


def choice_chip(label, selected, on_click):
    """A small selectable pill (used for the kg / lb switch)."""
    return ft.Container(
        bgcolor=ACCENT if selected else CARD_COLOR,
        border_radius=30,
        ink=True,
        on_click=on_click,
        padding=ft.Padding.symmetric(horizontal=18, vertical=10),
        border=ft.Border.all(1.5, ACCENT if selected else CARD_LIGHT),
        content=ft.Text(
            label, size=14, weight=ft.FontWeight.BOLD, color=BG_COLOR if selected else TEXT_PRIMARY
        ),
    )


def continue_button(label, enabled, on_click, icon=ft.Icons.ARROW_FORWARD_ROUNDED):
    """The bottom button. Greyed out until the question is answered."""
    if enabled:
        return primary_button(label, on_click, icon=icon)
    return ft.Container(
        height=60,
        bgcolor=CARD_LIGHT,
        border_radius=18,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Text(label, size=18, weight=ft.FontWeight.BOLD, color=TEXT_MUTED)],
        ),
    )


def build_onboarding_screen(page: ft.Page, on_complete, on_done):
    """The first-launch questions, one per screen.

    on_complete(answers)  saves the answers (apply_onboarding)
    on_done()             called right after saving, to open Home
    """
    answers = onboarding_defaults()
    state = {"step": 0}
    errors = {}  # error message for a number box, by question key
    area = ft.Container(expand=True)

    # ---------- answering ----------
    def choose(key, value):
        answers[key] = value
        render()

    def toggle_equipment(value):
        if value in ("No equipment", "Full gym"):
            answers["equipment"] = [value]  # these two stand alone
        else:
            current = [e for e in answers["equipment"] if e not in ("No equipment", "Full gym")]
            if value in current:
                current.remove(value)
            else:
                current.append(value)
            answers["equipment"] = current
        render()

    def bind(key):
        def handler(e):
            answers[key] = e.control.value
            errors.pop(key, None)
        return handler

    def set_units(new_units):
        old = units()
        if new_units == old:
            return
        for key in ("weight", "goal_weight"):  # convert anything already typed
            value = parse_number(answers[key])
            if value is not None:
                kg = value / KG_TO_LB if old == "lb" else value
                answers[key] = f"{(kg * KG_TO_LB if new_units == 'lb' else kg):.1f}"
        DATA["settings"]["units"] = new_units
        save_data()
        errors.clear()
        render()

    # ---------- the number questions ----------
    def number_info(key):
        """(title, subtitle, box label, unit text, lowest, highest, icon)"""
        wlow, whigh = (30, 300) if units() == "kg" else (66, 660)
        return {
            "height": ("How tall are you?", "Saved to your profile.", "Height", "cm", 100, 250, ft.Icons.HEIGHT),
            "weight": ("What is your current weight?", "This is your starting point.", "Current weight", units(), wlow, whigh, ft.Icons.MONITOR_WEIGHT),
            "age": ("How old are you?", "Saved to your profile.", "Age", "years", 10, 100, ft.Icons.CAKE_OUTLINED),
            "goal_weight": ("What is your goal weight?", "Enter your current weight again if you just want to maintain.", "Goal weight", units(), wlow, whigh, ft.Icons.FLAG_OUTLINED),
        }[key]

    def check_number(key) -> bool:
        _t, _s, label, unit, low, high, _i = number_info(key)
        value = parse_number(answers[key])
        if value is None or not (low <= value <= high):
            errors[key] = f"Enter a number between {low} and {high} {unit}"
            render()
            return False
        errors.pop(key, None)
        return True

    # ---------- moving between steps ----------
    def step_valid(key) -> bool:
        if key in ("height", "weight", "age", "goal_weight"):
            return True  # the number is checked when you press Continue
        if key == "equipment":
            return bool(answers["equipment"])
        return bool(answers[key])

    def go_next(e=None):
        key = ONBOARDING_STEPS[state["step"]]
        if not step_valid(key):
            return
        if key in ("height", "weight", "age", "goal_weight") and not check_number(key):
            return
        if state["step"] == len(ONBOARDING_STEPS) - 1:
            on_complete(dict(answers))
            on_done()
            return
        state["step"] += 1
        render()

    def go_back(e):
        if state["step"] > 0:
            state["step"] -= 1
            render()

    # ---------- drawing ----------
    def option_list(choices, key):
        return [
            option_card(label, sub, icon, answers[key] == label, lambda e, v=label: choose(key, v))
            for label, sub, icon in choices
        ]

    def number_controls(key):
        _t, _s, label, unit, _low, _high, icon = number_info(key)
        controls = [
            ft.Container(
                width=88,
                height=88,
                border_radius=44,
                bgcolor=CARD_COLOR,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, color=ACCENT, size=40),
            )
        ]
        if key in ("weight", "goal_weight"):
            controls.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        choice_chip("kg", units() == "kg", lambda e: set_units("kg")),
                        choice_chip("lb", units() == "lb", lambda e: set_units("lb")),
                    ],
                )
            )
        controls.append(
            styled_field(
                value=answers[key],
                label=label,
                suffix=ft.Text(unit, color=TEXT_MUTED),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=300,
                text_size=28,
                text_align=ft.TextAlign.CENTER,
                autofocus=True,
                error=errors.get(key),
                on_change=bind(key),
                on_submit=go_next,
            )
        )
        return controls

    def content_for(key):
        """Returns (title, subtitle, controls) for the current question."""
        if key == "goal":
            return "What is your main goal?", "We'll use this to personalize FitLife.", option_list(GOAL_CHOICES, "goal")
        if key == "level":
            return "What is your experience level?", "Be honest, it helps us get this right.", option_list(LEVEL_CHOICES, "level")
        if key == "location":
            return "Where do you train?", "Choose where most of your workouts happen.", option_list(LOCATION_CHOICES, "location")
        if key == "equipment":
            cards = [
                option_card(label, sub, icon, label in answers["equipment"], lambda e, v=label: toggle_equipment(v))
                for label, sub, icon in EQUIPMENT_CHOICES
            ]
            return "What equipment do you have?", "Choose everything that applies.", cards
        if key == "days":
            tiles = []
            for n in DAY_OPTIONS:
                selected = answers["days"] == n
                tiles.append(
                    ft.Container(
                        width=104,
                        height=100,
                        bgcolor=ACCENT if selected else CARD_COLOR,
                        border_radius=20,
                        ink=True,
                        border=ft.Border.all(2, ACCENT if selected else CARD_LIGHT),
                        on_click=lambda e, v=n: choose("days", v),
                        content=ft.Column(
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=2,
                            controls=[
                                ft.Text(str(n), size=34, weight=ft.FontWeight.BOLD, color=BG_COLOR if selected else TEXT_PRIMARY),
                                ft.Text("days / week", size=12, color=BG_COLOR if selected else TEXT_MUTED),
                            ],
                        ),
                    )
                )
            grid = ft.Row(wrap=True, spacing=12, run_spacing=12, controls=tiles)
            return "How many days per week can you train?", "Pick what you can realistically stick to.", [grid]
        if key == "duration":
            return "How long can each workout be?", "Choose the time you usually have.", option_list(DURATION_CHOICES, "duration")
        title, subtitle, *_rest = number_info(key)
        return title, subtitle, number_controls(key)

    def question_view():
        key = ONBOARDING_STEPS[state["step"]]
        total = len(ONBOARDING_STEPS)
        title, subtitle, controls = content_for(key)
        last = state["step"] == total - 1

        top = ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                            icon_color=TEXT_PRIMARY,
                            on_click=go_back,
                        )
                        if state["step"] > 0
                        else ft.Container(width=48, height=48),
                        ft.Text(f"Step {state['step'] + 1} of {total}", size=14, color=TEXT_MUTED),
                        ft.Container(width=48),
                    ],
                ),
                ft.ProgressBar(
                    value=(state["step"] + 1) / total,
                    color=ACCENT,
                    bgcolor=CARD_LIGHT,
                    bar_height=8,
                    border_radius=8,
                ),
            ],
        )
        return ft.Column(
            expand=True,
            spacing=14,
            controls=[
                top,
                screen_title(title, subtitle),
                ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    if key in ("height", "weight", "age", "goal_weight")
                    else ft.CrossAxisAlignment.STRETCH,
                    controls=controls,
                ),
                continue_button(
                    "FINISH" if last else "CONTINUE",
                    step_valid(key),
                    go_next,
                    icon=ft.Icons.CHECK_ROUNDED if last else ft.Icons.ARROW_FORWARD_ROUNDED,
                ),
            ],
        )

    def render():
        area.content = question_view()
        page.update()

    area.content = question_view()
    return area


def build_home_screen(page: ft.Page, act: Actions):
    """Home dashboard."""
    today = suggested_workout()
    trained_today = date.today() in workout_days()

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(
                        width=42,
                        height=42,
                        bgcolor=ACCENT,
                        border_radius=14,
                        content=ft.Icon(ft.Icons.FITNESS_CENTER, color=BG_COLOR, size=24),
                    ),
                    ft.Text("FitLife", size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ],
            ),
            ft.Container(
                width=42,
                height=42,
                bgcolor=CARD_COLOR,
                border_radius=21,
                ink=True,
                on_click=lambda e: act.go_tab(3),
                content=ft.Icon(ft.Icons.PERSON, color=TEXT_MUTED, size=24),
            ),
        ],
    )

    subtitle = (
        "You already trained today. Great work! 💪"
        if trained_today
        else f"Ready for {today['name']}?"
    )
    greeting = ft.Column(
        spacing=2,
        controls=[
            ft.Text(greeting_text(), size=30, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text(subtitle, size=15, color=TEXT_MUTED),
        ],
    )

    # --- Weight card (tap it to log your weight) ---
    progress = weight_progress()
    percent_text = "Goal reached! 🎉" if progress >= 1 else f"{int(progress * 100)}% of the way to your goal"
    weight_card = ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        ink=True,
        on_click=lambda e: show_log_weight_dialog(page, act.refresh),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Your Progress", size=16, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                        ft.Text("+ Log weight", size=13, color=ACCENT),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("Current", size=13, color=TEXT_MUTED),
                                ft.Text(
                                    fmt_weight(DATA["weights"][-1]["kg"]),
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                            ],
                        ),
                        ft.Column(
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                ft.Text("Goal", size=13, color=TEXT_MUTED),
                                ft.Text(
                                    fmt_weight(DATA["profile"]["goal_kg"]),
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=ACCENT,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.ProgressBar(
                    value=progress,
                    color=ACCENT,
                    bgcolor=CARD_LIGHT,
                    bar_height=10,
                    border_radius=10,
                ),
                ft.Text(percent_text, size=13, color=TEXT_MUTED),
            ],
        ),
    )

    # --- Today's workout ---
    workout_card = ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text("Today's Workout", size=16, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                ft.Text(today["name"], size=30, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Row(
                    spacing=10,
                    controls=[
                        info_chip(ft.Icons.TIMER_OUTLINED, today["duration"]),
                        info_chip(ft.Icons.LIST_ALT_ROUNDED, f"{len(today['exercises'])} Exercises"),
                    ],
                ),
                primary_button("START WORKOUT", lambda e: act.open_workout(today)),
            ],
        ),
    )

    # --- My 30-day journey (only when a plan is saved) ---
    journey_card = build_journey_card(act)

    # --- Quick stats (real numbers from your history) ---
    week = this_week_history()
    week_seconds = sum(h["seconds"] for h in week)
    streak = current_streak()
    go_progress = lambda e: act.go_tab(2)
    quick_stats = ft.Column(
        spacing=12,
        controls=[
            section_title("This Week"),
            ft.Row(
                spacing=12,
                controls=[
                    stat_tile(ft.Icons.FITNESS_CENTER, "Workouts", str(len(week)), go_progress),
                    stat_tile(ft.Icons.ACCESS_TIME_ROUNDED, "Total Time", format_duration(week_seconds), go_progress),
                    stat_tile(
                        ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
                        "Streak",
                        f"{streak} day{'s' if streak != 1 else ''}",
                        go_progress,
                    ),
                ],
            ),
        ],
    )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        expand=True,
        controls=[header, greeting, weight_card] + ([journey_card] if journey_card else []) + [workout_card, quick_stats],
    )


# ---------------------------------------------------------------
# MY 30-DAY PLAN (reads the saved plan; never generates anything)
# ---------------------------------------------------------------
def saved_plan_days():
    """The saved plan entries in Day order (skips anything that is not a proper day)."""
    plan = DATA.get("thirty_day_plan")
    if not isinstance(plan, list):
        return []
    days = [d for d in plan if isinstance(d, dict) and isinstance(d.get("day"), int)]
    return sorted(days, key=lambda d: d["day"])


def plan_current_day():
    """current_program_day, kept inside 1..30."""
    value = DATA.get("current_program_day", 1)
    if not isinstance(value, int) or isinstance(value, bool):
        value = 1
    return max(1, min(PLAN_LENGTH, value))


def plan_completed_days():
    """Days listed in completed_program_days (and nothing else counts as completed)."""
    done = DATA.get("completed_program_days")
    return {d for d in done if isinstance(d, int)} if isinstance(done, list) else set()


def complete_program_day(day, workout=None) -> bool:
    """Mark one plan day as completed and move current_program_day forward.

    Returns True only if something changed. Never raises for bad or missing data.
    Rules: the day must exist in the saved plan, must not be a rest day, must match the
    workout that was just finished, and must not already be completed. The current day
    never moves backwards. Rest days are never completed here.
    """
    try:
        if not isinstance(day, int) or isinstance(day, bool):
            return False
        days = saved_plan_days()
        entry = next((d for d in days if d["day"] == day), None)
        if entry is None or entry.get("type") == "rest":
            return False
        if isinstance(workout, dict):
            if workout.get("name") != entry.get("title"):
                return False                      # not the workout this plan day contains
            if workout.get("program_day") not in (None, day):
                return False
        done = {d for d in plan_completed_days() if 1 <= d <= PLAN_LENGTH}
        if day in done:
            return False                          # already completed: no duplicates
        done.add(day)
        later = [d["day"] for d in days if d["day"] > day and d["day"] not in done]
        new_current = max(plan_current_day(), later[0] if later else day)
        DATA["completed_program_days"] = sorted(done)
        DATA["current_program_day"] = min(PLAN_LENGTH, new_current)
        return True
    except Exception as error:
        print("Could not update the 30-day plan:", error)
        return False


def build_journey_card(act: Actions):
    """Home: MY 30-DAY JOURNEY card with today's plan. None when no 30-day plan is saved."""
    days = saved_plan_days()
    if len(days) != PLAN_LENGTH:
        return None
    current = plan_current_day()
    completed = {d for d in plan_completed_days() if 1 <= d <= PLAN_LENGTH}
    done_count = len(completed)
    entry = next((d for d in days if d["day"] == current), None)

    def label(text, color=TEXT_MUTED):
        return ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=color)

    def panel(*controls):
        return ft.Container(
            bgcolor=CARD_LIGHT,
            border_radius=18,
            padding=ft.Padding.all(16),
            content=ft.Column(spacing=6, controls=list(controls)),
        )

    view_plan = secondary_button("VIEW PLAN", lambda e: act.open_plan(), icon=ft.Icons.CALENDAR_MONTH_ROUNDED)

    # ---- all 30 days completed
    if done_count >= PLAN_LENGTH:
        return ft.Container(
            bgcolor=CARD_COLOR,
            border_radius=24,
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text("30-DAY JOURNEY COMPLETE 🎉", size=22, weight=ft.FontWeight.BOLD, color=ACCENT),
                    ft.ProgressBar(value=1.0, color=ACCENT, bgcolor=CARD_LIGHT, bar_height=10, border_radius=10),
                    ft.Text(f"{PLAN_LENGTH} of {PLAN_LENGTH} days completed", size=14, color=TEXT_MUTED),
                    view_plan,
                ],
            ),
        )

    # ---- today's panel + button
    title, subtitle, kind = plan_day_info(entry) if entry else ("", "", "rest")
    workout = None
    if entry and kind != "rest":
        try:
            workout = plan_day_workout(entry)
        except Exception:
            workout = None
        if workout is not None and not workout.get("exercises"):
            workout = None

    if entry is None or (kind != "rest" and workout is None):
        # something is wrong with this day's data: stay calm and just offer the plan
        today_panel = panel(
            label("TODAY"),
            ft.Text("Open your plan to see today's session.", size=15, color=TEXT_MUTED),
        )
        action = view_plan
    elif kind == "rest":
        today_panel = panel(
            label("TODAY"),
            ft.Text("REST DAY", size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text("Recovery is part of your 30-day journey.", size=14, color=TEXT_MUTED),
        )
        action = view_plan
    elif current in completed:
        today_panel = panel(
            label("TODAY'S WORKOUT", ACCENT),
            ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text("Completed ✅", size=14, color=ACCENT),
        )
        action = view_plan
    else:
        today_panel = panel(
            label("TODAY'S WORKOUT", ACCENT),
            ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text(subtitle, size=14, color=TEXT_MUTED),
        )
        action = primary_button("START TODAY'S WORKOUT", lambda e, w=workout: act.open_plan_workout(w))

    controls = [
        ft.Text("MY 30-DAY JOURNEY", size=14, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
        ft.Text(f"Day {current} of {PLAN_LENGTH}", size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ft.ProgressBar(value=current / PLAN_LENGTH, color=ACCENT, bgcolor=CARD_LIGHT, bar_height=10, border_radius=10),
        ft.Text(f"{done_count} day{'' if done_count == 1 else 's'} completed", size=13, color=TEXT_MUTED),
        today_panel,
        action,
    ]
    # a workout day has a big START button, so the plan link is a small one underneath
    if action is not view_plan:
        controls.append(
            ft.Container(
                alignment=ft.Alignment.CENTER,
                content=ft.TextButton("View full plan", on_click=lambda e: act.open_plan(), style=ft.ButtonStyle(color=TEXT_MUTED)),
            )
        )
    return ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        content=ft.Column(spacing=14, controls=controls),
    )


def plan_day_info(entry: dict):
    """Text for one plan day: (title, subtitle, kind) where kind is workout / recovery / rest."""
    kind = entry.get("type") if entry.get("type") in ("workout", "recovery", "rest") else "workout"
    if kind == "rest":
        return "Rest Day", "Recovery / Rest", kind
    title = str(entry.get("title") or "Workout")
    parts = []
    if isinstance(entry.get("duration_min"), (int, float)):
        parts.append(f"{int(entry['duration_min'])} min")
    count = entry.get("exercise_count")
    if not isinstance(count, int):
        count = len(entry.get("exercises") or [])
    if count:
        parts.append(f"{count} exercises")
    return title, " · ".join(parts), kind


def show_rest_day_dialog(page: ft.Page):
    page.show_dialog(
        ft.AlertDialog(
            bgcolor=CARD_COLOR,
            title=ft.Text("Rest Day", color=TEXT_PRIMARY),
            content=ft.Text("Recovery is part of your 30-day journey.", color=TEXT_MUTED),
            actions=[dialog_button("Close", lambda e: page.pop_dialog())],
        )
    )


def plan_day_card(entry: dict, current: int, completed: set, on_tap):
    """One row of the plan list: completed / current / upcoming, workout / recovery / rest."""
    day = entry["day"]
    title, subtitle, kind = plan_day_info(entry)
    is_done = day in completed
    is_current = day == current
    is_rest = kind == "rest"

    # round badge on the left
    if is_done:
        badge = ft.Container(
            width=44, height=44, border_radius=22, bgcolor=ACCENT, alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.CHECK_ROUNDED, color=BG_COLOR, size=26),
        )
    elif is_rest:
        badge = ft.Container(
            width=44, height=44, border_radius=22, bgcolor=CARD_LIGHT, alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.BEDTIME_OUTLINED, color=TEXT_MUTED, size=22),
        )
    elif is_current:
        badge = ft.Container(
            width=44, height=44, border_radius=22, bgcolor=ACCENT, alignment=ft.Alignment.CENTER,
            content=ft.Text(str(day), size=17, weight=ft.FontWeight.BOLD, color=BG_COLOR),
        )
    else:
        badge = ft.Container(
            width=44, height=44, border_radius=22, bgcolor=CARD_LIGHT, alignment=ft.Alignment.CENTER,
            content=ft.Text(str(day), size=17, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
        )

    # small label above the title
    label = f"DAY {day}"
    if is_current:
        label += "  ·  TODAY"
    label_color = ACCENT if is_current else TEXT_MUTED

    # tag on the right
    if is_done:
        tag_text, tag_bg, tag_fg = "COMPLETED", ACCENT, BG_COLOR
    elif is_rest:
        tag_text, tag_bg, tag_fg = "REST DAY", CARD_LIGHT, TEXT_MUTED
    elif kind == "recovery":
        tag_text, tag_bg, tag_fg = "RECOVERY", CARD_LIGHT, TEXT_PRIMARY
    else:
        tag_text, tag_bg, tag_fg = "WORKOUT", CARD_LIGHT, ACCENT
    tag = ft.Container(
        bgcolor=tag_bg, border_radius=30, padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        content=ft.Text(tag_text, size=11, weight=ft.FontWeight.BOLD, color=tag_fg),
    )

    texts = [
        ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=label_color),
        ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=TEXT_MUTED if is_rest else TEXT_PRIMARY),
    ]
    if subtitle:
        texts.append(ft.Text(subtitle, size=13, color=TEXT_MUTED))

    return ft.Container(
        bgcolor=BG_COLOR if is_rest and not is_current else CARD_COLOR,
        border_radius=20,
        padding=ft.Padding.all(14),
        border=ft.Border.all(2, ACCENT) if is_current else ft.Border.all(1, CARD_LIGHT if is_rest else CARD_COLOR),
        opacity=1.0 if (is_current or is_done) else 0.8,
        ink=True,
        on_click=lambda e, entry=entry: on_tap(entry),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                badge,
                ft.Column(spacing=2, expand=True, controls=texts),
                tag,
            ],
        ),
    )


def build_plan_screen(page: ft.Page, on_back, on_open_workout):
    """My 30-Day Plan: shows the plan that is already saved in DATA."""
    days = saved_plan_days()
    current = plan_current_day()
    completed = plan_completed_days()

    def tap_day(entry):
        title, _, kind = plan_day_info(entry)
        if kind == "rest":
            show_rest_day_dialog(page)
            return
        try:
            workout = plan_day_workout(entry)
        except Exception:
            workout = None
        if not workout or not workout.get("exercises"):
            toast(page, "This workout isn't available right now.")
            return
        on_open_workout(workout)

    top_bar = ft.Row(
        spacing=4,
        controls=[
            ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=TEXT_PRIMARY, on_click=on_back),
            ft.Text("My 30-Day Plan", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ],
    )

    journey = ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text("30-Day Journey", size=15, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                ft.Text(f"Day {current} of {PLAN_LENGTH}", size=30, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.ProgressBar(value=current / PLAN_LENGTH, color=ACCENT, bgcolor=CARD_LIGHT, bar_height=10, border_radius=10),
            ],
        ),
    )

    if days:
        cards = [plan_day_card(d, current, completed, tap_day) for d in days]
    else:
        cards = [
            ft.Container(
                bgcolor=CARD_COLOR, border_radius=20, padding=ft.Padding.all(20),
                content=ft.Text("Your plan isn't ready yet. Finish onboarding to get your 30-day plan.", size=14, color=TEXT_MUTED),
            )
        ]

    return ft.Column(
        spacing=16,
        expand=True,
        controls=[
            top_bar,
            ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
                expand=True,
                controls=[journey, *cards, ft.Container(height=10)],
            ),
        ],
    )


def build_fitness_plan_screen(page: ft.Page, on_back, on_view_plan, on_refresh):
    """Fitness Plan: your saved onboarding answers, your numbers and a 30-day summary.
    Read-only view of DATA (numbers are edited with the existing Profile / weight dialogs)."""
    profile = DATA.get("profile") or {}

    def text_or_dash(value):
        return str(value) if value not in (None, "", []) else "—"

    equipment = DATA.get("equipment")
    equipment_text = ", ".join(str(x) for x in equipment) if isinstance(equipment, list) and equipment else "—"
    days_per_week = DATA.get("training_days_per_week")
    frequency_text = f"{days_per_week} days per week" if isinstance(days_per_week, int) and days_per_week > 0 else "—"

    try:
        current_weight = f"{to_display(DATA['weights'][-1]['kg']):.1f} {units()}"
    except Exception:
        current_weight = "—"
    try:
        goal_weight = f"{to_display(profile['goal_kg']):.1f} {units()}"
    except Exception:
        goal_weight = "—"
    height_text = f"{profile['height_cm']} cm" if profile.get("height_cm") else "—"
    age_text = text_or_dash(profile.get("age"))

    def info_row(label, value):
        return ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(width=118, content=ft.Text(label, size=14, color=TEXT_MUTED)),
                ft.Text(value, size=15, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY, expand=True, text_align=ft.TextAlign.RIGHT),
            ],
        )

    def card(*controls):
        return ft.Container(
            bgcolor=CARD_COLOR,
            border_radius=24,
            padding=ft.Padding.all(20),
            content=ft.Column(spacing=12, controls=list(controls)),
        )

    def card_label(text):
        return ft.Text(text, size=14, weight=ft.FontWeight.W_600, color=TEXT_MUTED)

    top_bar = ft.Row(
        spacing=4,
        controls=[
            ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=TEXT_PRIMARY, on_click=on_back),
            ft.Text("Fitness Plan", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ],
    )

    setup_card = card(
        card_label("YOUR FITNESS PLAN"),
        info_row("Goal", text_or_dash(DATA.get("fitness_goal"))),
        info_row("Experience", text_or_dash(DATA.get("experience_level"))),
        info_row("Training location", text_or_dash(DATA.get("training_location"))),
        info_row("Equipment", equipment_text),
        info_row("Training frequency", frequency_text),
        info_row("Workout duration", text_or_dash(DATA.get("workout_duration"))),
    )

    numbers_card = card(
        card_label("YOUR NUMBERS"),
        info_row("Current weight", current_weight),
        info_row("Goal weight", goal_weight),
        info_row("Height", height_text),
        info_row("Age", age_text),
        ft.Row(
            alignment=ft.MainAxisAlignment.END,
            spacing=4,
            controls=[
                ft.TextButton("Log weight", on_click=lambda e: show_log_weight_dialog(page, on_refresh), style=ft.ButtonStyle(color=ACCENT)),
                ft.TextButton("Edit profile", on_click=lambda e: show_edit_profile_dialog(page, on_refresh), style=ft.ButtonStyle(color=ACCENT)),
            ],
        ),
    )

    days = saved_plan_days()
    if len(days) == PLAN_LENGTH:
        current = plan_current_day()
        completed = {d for d in plan_completed_days() if 1 <= d <= PLAN_LENGTH}
        entry = next((d for d in days if d["day"] == current), None)
        if entry is None:
            status = "—"
        else:
            title, subtitle, kind = plan_day_info(entry)
            if kind == "rest":
                status = "Rest Day"
            elif current in completed:
                status = f"{title} · Completed ✅"
            else:
                status = f"{title} · {subtitle}" if subtitle else title
        journey_card = card(
            card_label("30-DAY JOURNEY"),
            ft.Text(f"Day {current} of {PLAN_LENGTH}", size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.ProgressBar(value=current / PLAN_LENGTH, color=ACCENT, bgcolor=CARD_LIGHT, bar_height=10, border_radius=10),
            info_row("Completed days", str(len(completed))),
            info_row("Remaining days", str(PLAN_LENGTH - len(completed))),
            ft.Container(
                bgcolor=CARD_LIGHT,
                border_radius=16,
                padding=ft.Padding.all(14),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text("TODAY", size=12, weight=ft.FontWeight.W_600, color=ACCENT),
                        ft.Text(status, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ],
                ),
            ),
        )
        bottom = [journey_card, primary_button("VIEW 30-DAY PLAN", lambda e: on_view_plan(), icon=ft.Icons.CALENDAR_MONTH_ROUNDED)]
    else:
        bottom = [card(card_label("30-DAY JOURNEY"), ft.Text("Your 30-day plan isn't ready yet.", size=14, color=TEXT_MUTED))]

    return ft.Column(
        spacing=16,
        expand=True,
        controls=[
            top_bar,
            ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
                expand=True,
                controls=[setup_card, numbers_card, *bottom, ft.Container(height=10)],
            ),
        ],
    )


def build_workouts_screen(page: ft.Page, act: Actions):
    """Workouts tab with two views: Programs and Exercise Library."""
    view = {"name": "programs"}

    tabs_row = ft.Row(spacing=10)
    list_area = ft.Column(spacing=12)
    search_field = styled_field(
        hint_text="Search exercises",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=16,
        filled=True,
        bgcolor=CARD_COLOR,
        on_change=lambda e: fill_list(update=True),
    )

    def tab_pill(label, key):
        selected = view["name"] == key
        return ft.Container(
            bgcolor=ACCENT if selected else CARD_COLOR,
            border_radius=30,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            on_click=lambda e: switch(key),
            content=ft.Text(
                label,
                size=14,
                weight=ft.FontWeight.BOLD,
                color=BG_COLOR if selected else TEXT_PRIMARY,
            ),
        )

    def fill_list(update=False):
        if view["name"] == "programs":
            list_area.controls = [workout_list_item(w, act.open_workout) for w in WORKOUTS]
        else:
            query = (search_field.value or "").strip().lower()
            matches = [
                ex for ex in all_exercises()
                if query in ex["name"].lower() or query in ex["muscle"].lower()
            ]
            if matches:
                list_area.controls = [library_item(ex, lambda item: show_exercise_sheet(page, item)) for ex in matches]
            else:
                list_area.controls = [ft.Text("No exercises found.", color=TEXT_MUTED)]
        if update:
            list_area.update()

    def switch(key):
        view["name"] = key
        tabs_row.controls = [tab_pill("Programs", "programs"), tab_pill("Exercises", "exercises")]
        search_field.visible = key == "exercises"
        fill_list()
        tabs_row.update()
        search_field.update()
        list_area.update()

    # Initial draw (before the controls are on the page, so no update() calls).
    tabs_row.controls = [tab_pill("Programs", "programs"), tab_pill("Exercises", "exercises")]
    search_field.visible = False
    fill_list()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        expand=True,
        controls=[
            screen_title("Workouts", "Choose a program or browse exercises"),
            tabs_row,
            search_field,
            list_area,
        ],
    )


def build_workout_detail_screen(page: ft.Page, workout: dict, on_back, on_start):
    """Detail screen for one workout."""
    exercises = workout["exercises"]
    total_sets = sum(ex["sets"] for ex in exercises)

    top_bar = ft.Row(
        spacing=4,
        controls=[
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color=TEXT_PRIMARY,
                on_click=on_back,
            ),
            ft.Text("Workout", size=16, color=TEXT_MUTED),
        ],
    )

    header = ft.Column(
        spacing=12,
        controls=[
            ft.Text(workout["name"], size=32, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text(workout["description"], size=15, color=TEXT_MUTED),
            ft.Row(
                wrap=True,
                spacing=10,
                run_spacing=10,
                controls=[
                    info_chip(ft.Icons.TIMER_OUTLINED, workout["duration"]),
                    info_chip(ft.Icons.LIST_ALT_ROUNDED, f"{len(exercises)} exercises"),
                    info_chip(ft.Icons.REPEAT_ROUNDED, f"{total_sets} sets"),
                    info_chip(ft.Icons.TRENDING_UP, workout["level"]),
                ],
            ),
        ],
    )

    exercise_cards = [
        exercise_item(i + 1, ex, lambda item: show_exercise_sheet(page, item))
        for i, ex in enumerate(exercises)
    ]

    scrolling_part = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        expand=True,
        controls=[
            header,
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    section_title("Exercises"),
                    ft.Text("Tap one for instructions", size=12, color=TEXT_MUTED),
                ],
            ),
            ft.Column(spacing=10, controls=exercise_cards),
        ],
    )

    return ft.Column(
        expand=True,
        spacing=12,
        controls=[top_bar, scrolling_part, primary_button("START WORKOUT", on_start)],
    )


def build_workout_player_screen(page: ft.Page, workout: dict, on_exit, on_finish):
    """The workout player: exercise -> rest timer -> next set -> finished.

    on_exit()                        called when the user quits early.
    on_finish(workout, seconds, sets) called when the user taps DONE at the end.
    """
    exercises = workout["exercises"]
    total_sets = sum(ex["sets"] for ex in exercises)

    # The "state" remembers where the user is in the workout.
    state = {
        "phase": "exercise",     # "exercise", "rest" or "done"
        "ex_index": 0,
        "set_index": 0,
        "sets_done": 0,
        "rest_left": 0,
        "rest_total": 1,
        "timer_id": 0,           # lets us stop old timers
        "active": True,          # False once the user leaves the player
        "started_at": time.time(),
        "elapsed_seconds": 0,
        "rest_text": None,
        "rest_ring": None,
    }

    content_area = ft.Container(expand=True)

    # ---------- Actions ----------
    def complete_set(e):
        ex = exercises[state["ex_index"]]
        state["sets_done"] += 1

        is_last_set = state["set_index"] == ex["sets"] - 1
        is_last_exercise = state["ex_index"] == len(exercises) - 1

        if is_last_set and is_last_exercise:
            finish_workout()
            return

        if is_last_set:
            state["ex_index"] += 1
            state["set_index"] = 0
        else:
            state["set_index"] += 1

        start_rest(ex["rest"])

    def start_rest(seconds: int):
        state["phase"] = "rest"
        state["rest_left"] = seconds
        state["rest_total"] = seconds
        state["timer_id"] += 1
        render()
        page.run_task(rest_timer, state["timer_id"])

    def end_rest(e=None):
        state["timer_id"] += 1  # this stops the running timer
        state["phase"] = "exercise"
        render()

    def add_rest_time(e):
        state["rest_left"] += 15
        state["rest_total"] = max(state["rest_total"], state["rest_left"])
        update_rest_display()

    def finish_workout():
        state["timer_id"] += 1
        state["elapsed_seconds"] = int(time.time() - state["started_at"])
        state["phase"] = "done"
        render()

    def on_done(e):
        state["active"] = False
        on_finish(workout, state["elapsed_seconds"], total_sets)

    def ask_quit(e):
        def quit_now(ev):
            page.pop_dialog()
            state["active"] = False
            state["timer_id"] += 1
            on_exit()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                bgcolor=CARD_COLOR,
                title=ft.Text("Quit workout?", color=TEXT_PRIMARY),
                content=ft.Text("Your progress in this session will not be saved.", color=TEXT_MUTED),
                actions=[
                    dialog_button("Keep going", lambda ev: page.pop_dialog()),
                    dialog_button("Quit", quit_now, color=DANGER),
                ],
            )
        )

    # ---------- Rest timer (runs in the background) ----------
    async def rest_timer(my_id):
        """Counts down once per second until the rest is over."""
        while True:
            await asyncio.sleep(1)
            if not state["active"] or state["timer_id"] != my_id or state["phase"] != "rest":
                return
            state["rest_left"] -= 1
            if state["rest_left"] <= 0:
                end_rest()
                return
            update_rest_display()

    def update_rest_display():
        """Refresh only the countdown text and circle."""
        if state["rest_text"] is None or state["rest_ring"] is None:
            return
        state["rest_text"].value = format_time(state["rest_left"])
        state["rest_ring"].value = state["rest_left"] / state["rest_total"]
        state["rest_text"].update()
        state["rest_ring"].update()

    # ---------- Drawing the screen ----------
    def player_header():
        overall = state["sets_done"] / total_sets
        return ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_color=TEXT_PRIMARY, on_click=ask_quit),
                        ft.Text(workout["name"], size=16, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                        ft.Text(f"{state['sets_done']}/{total_sets} sets", size=14, color=ACCENT),
                    ],
                ),
                ft.ProgressBar(
                    value=overall,
                    color=ACCENT,
                    bgcolor=CARD_LIGHT,
                    bar_height=8,
                    border_radius=8,
                ),
            ],
        )

    def exercise_view():
        ex = exercises[state["ex_index"]]
        set_number = state["set_index"] + 1

        dots = []
        for i in range(ex["sets"]):
            if i < state["set_index"]:
                dot_color = ACCENT
            elif i == state["set_index"]:
                dot_color = TEXT_PRIMARY
            else:
                dot_color = CARD_LIGHT
            dots.append(ft.Container(width=14, height=14, border_radius=7, bgcolor=dot_color))

        demo_box = ft.Container(
            expand=True,
            height=170,
            bgcolor=CARD_COLOR,
            border_radius=24,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, size=56, color=ACCENT),
                    ft.Text("Demo video coming soon", size=13, color=TEXT_MUTED),
                ],
            ),
        )

        middle = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    f"EXERCISE {state['ex_index'] + 1} OF {len(exercises)}",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=TEXT_MUTED,
                ),
                ft.Row(controls=[demo_box]),
                ft.Text(
                    ex["name"],
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        info_chip(ft.Icons.FITNESS_CENTER, ex["muscle"]),
                        pill_button(
                            ft.Icons.HELP_OUTLINE,
                            "How to",
                            lambda e: show_exercise_sheet(page, ex),
                        ),
                    ],
                ),
                ft.Text(
                    f"SET {set_number} OF {ex['sets']}",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ACCENT,
                ),
                ft.Text(ex["reps"], size=44, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10, controls=dots),
            ],
        )

        return ft.Column(
            expand=True,
            spacing=12,
            controls=[
                player_header(),
                middle,
                primary_button("COMPLETE SET", complete_set, icon=ft.Icons.CHECK_ROUNDED),
            ],
        )

    def rest_view():
        next_ex = exercises[state["ex_index"]]
        next_set_number = state["set_index"] + 1

        ring = ft.ProgressRing(
            value=state["rest_left"] / state["rest_total"],
            width=220,
            height=220,
            stroke_width=12,
            color=ACCENT,
            bgcolor=CARD_LIGHT,
        )
        countdown = ft.Text(
            format_time(state["rest_left"]),
            size=56,
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
        )
        state["rest_ring"] = ring
        state["rest_text"] = countdown

        ring_with_text = ft.Stack(
            width=220,
            height=220,
            controls=[
                ring,
                ft.Container(width=220, height=220, alignment=ft.Alignment.CENTER, content=countdown),
            ],
        )

        up_next = ft.Container(
            expand=True,
            bgcolor=CARD_COLOR,
            border_radius=20,
            padding=ft.Padding.all(16),
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=ACCENT, size=26),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text("UP NEXT", size=11, color=TEXT_MUTED),
                            ft.Text(next_ex["name"], size=17, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text(
                                f"Set {next_set_number} of {next_ex['sets']}  •  {next_ex['reps']}",
                                size=13,
                                color=ACCENT,
                            ),
                        ],
                    ),
                ],
            ),
        )

        middle = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
            controls=[
                ft.Text("REST", size=18, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                ring_with_text,
                ft.Row(controls=[up_next]),
            ],
        )

        add_button = secondary_button("+15 sec", add_rest_time, icon=ft.Icons.ADD)
        add_button.expand = True
        skip_button = primary_button("SKIP REST", end_rest, icon=ft.Icons.SKIP_NEXT_ROUNDED)
        skip_button.expand = True

        return ft.Column(
            expand=True,
            spacing=12,
            controls=[player_header(), middle, ft.Row(spacing=12, controls=[add_button, skip_button])],
        )

    def done_view():
        middle = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, size=90, color=ACCENT),
                ft.Text(
                    "Workout Complete! 🎉",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(f"{workout['name']} finished. Great job!", size=15, color=TEXT_MUTED),
                ft.Container(height=8),
                ft.Row(
                    spacing=12,
                    controls=[
                        stat_tile(ft.Icons.TIMER_OUTLINED, "Time", format_time(state["elapsed_seconds"])),
                        stat_tile(ft.Icons.LIST_ALT_ROUNDED, "Exercises", str(len(exercises))),
                        stat_tile(ft.Icons.REPEAT_ROUNDED, "Sets", str(total_sets)),
                    ],
                ),
            ],
        )
        return ft.Column(
            expand=True,
            spacing=12,
            controls=[middle, primary_button("DONE", on_done, icon=ft.Icons.CHECK_ROUNDED)],
        )

    def set_view():
        if state["phase"] == "exercise":
            content_area.content = exercise_view()
        elif state["phase"] == "rest":
            content_area.content = rest_view()
        else:
            content_area.content = done_view()

    def render():
        set_view()
        page.update()

    set_view()
    return content_area


def build_progress_screen(page: ft.Page, act: Actions):
    """Progress tab: weight chart, this week, workout history."""
    weights = DATA["weights"]
    change = weights[0]["kg"] - weights[-1]["kg"]      # positive = lost weight
    left = weights[-1]["kg"] - DATA["profile"]["goal_kg"]

    if abs(change) < 0.05:
        change_text = "No change yet"
    elif change > 0:
        change_text = f"-{to_display(change):.1f} {units()}"
    else:
        change_text = f"+{to_display(-change):.1f} {units()}"

    if abs(left) < 0.05:
        left_text = "Goal reached 🎉"
        left_caption = ""
    else:
        left_text = f"{to_display(abs(left)):.1f} {units()}"
        left_caption = "to your goal"

    weight_card = ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text("Weight", size=16, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(change_text, size=32, weight=ft.FontWeight.BOLD, color=ACCENT),
                                ft.Text("since you started", size=13, color=TEXT_MUTED),
                            ],
                        ),
                        ft.Column(
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                ft.Text(left_text, size=22, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                ft.Text(left_caption, size=13, color=TEXT_MUTED),
                            ],
                        ),
                    ],
                ),
                weight_bar_chart(),
                secondary_button(
                    "LOG WEIGHT",
                    lambda e: show_log_weight_dialog(page, act.refresh),
                    icon=ft.Icons.ADD,
                ),
            ],
        ),
    )

    trained_days = sum(1 for _, done, _ in week_activity() if done)
    week_card = ft.Container(
        bgcolor=CARD_COLOR,
        border_radius=24,
        padding=ft.Padding.all(20),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("This Week", size=16, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                        ft.Text(f"{trained_days} of 7 days", size=14, color=ACCENT),
                    ],
                ),
                week_row(),
            ],
        ),
    )

    history = DATA["history"][:10]
    if history:
        history_area = ft.Column(
            spacing=10,
            controls=[history_item(item, lambda it: show_history_sheet(page, it)) for item in history],
        )
    else:
        history_area = ft.Text("No workouts yet. Start one from Home!", color=TEXT_MUTED)

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        expand=True,
        controls=[
            screen_title("Progress", "Keep going, you're doing great"),
            weight_card,
            week_card,
            section_title("Recent Workouts"),
            history_area,
        ],
    )


def build_profile_screen(page: ft.Page, act: Actions):
    """Profile tab: your details and settings."""
    profile = DATA["profile"]
    initials = "".join(word[0] for word in profile["name"].split()[:2]).upper() or "?"
    edit = lambda e: show_edit_profile_dialog(page, act.refresh)

    avatar_area = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
        controls=[
            ft.Container(
                width=96,
                height=96,
                border_radius=48,
                bgcolor=ACCENT,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=edit,
                content=ft.Text(initials, size=36, weight=ft.FontWeight.BOLD, color=BG_COLOR),
            ),
            ft.Text(profile["name"], size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text(goal_label(), size=14, color=TEXT_MUTED),
        ],
    )

    info_row = ft.Row(
        spacing=12,
        controls=[
            stat_tile(ft.Icons.HEIGHT, "Height", f"{profile['height_cm']} cm", edit),
            stat_tile(ft.Icons.CAKE_OUTLINED, "Age", str(profile["age"]), edit),
            stat_tile(ft.Icons.TRENDING_UP, "Level", profile["level"], edit),
        ],
    )

    # --- Settings actions ---
    def toggle_units(e):
        DATA["settings"]["units"] = "lb" if units() == "kg" else "kg"
        save_data()
        act.refresh()
        toast(page, f"Units changed to {units()}")

    def toggle_notifications(e):
        DATA["settings"]["notifications"] = bool(e.control.value)
        save_data()
        state_text = "on" if e.control.value else "off"
        toast(page, f"Workout reminders {state_text}")

    notif_switch = ft.Switch(
        value=DATA["settings"]["notifications"],
        active_color=ACCENT,
        on_change=toggle_notifications,
    )

    def show_help(e):
        show_message_dialog(
            page,
            "Help & Support",
            "Tap a workout to see its exercises. Tap an exercise for instructions. "
            "Tap the weight card on Home to log your weight.\n\n"
            "Questions? support@fitlife.app (placeholder)",
        )

    def show_about(e):
        show_message_dialog(
            page,
            "About FitLife",
            "FitLife v0.8\nYour personal digital gym coach.\n\nAll data is stored on this device.",
        )

    settings = ft.Column(
        spacing=10,
        controls=[
            settings_row(ft.Icons.ASSIGNMENT_OUTLINED, "Fitness Plan", lambda e: act.open_fitness_plan()),
            settings_row(ft.Icons.EDIT_OUTLINED, "Edit Profile", edit),
            settings_row(
                ft.Icons.STRAIGHTEN,
                "Units",
                toggle_units,
                trailing=ft.Text(units(), size=15, weight=ft.FontWeight.BOLD, color=ACCENT),
            ),
            settings_row(ft.Icons.NOTIFICATIONS_OUTLINED, "Workout reminders", trailing=notif_switch),
            settings_row(ft.Icons.HELP_OUTLINE, "Help & Support", show_help),
            settings_row(ft.Icons.INFO_OUTLINE, "About FitLife", show_about),
            settings_row(
                ft.Icons.DELETE_OUTLINE,
                "Reset all data",
                lambda e: show_reset_dialog(page, act.start_app),
            ),
        ],
    )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        expand=True,
        controls=[
            screen_title("Profile", "Your details and settings"),
            avatar_area,
            info_row,
            section_title("Settings"),
            settings,
            ft.Text("FitLife v0.8", size=12, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
        ],
    )


# ---------------------------------------------------------------
# 8. MAIN APP (page setup + navigation)
# ---------------------------------------------------------------
def main(page: ft.Page):
    load_data()
    ensure_plan()
    summary = format_plan_summary()
    try:
        print(summary)
    except Exception:
        print(summary.encode("ascii", "replace").decode())

    page.title = "FitLife"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_COLOR
    page.padding = 0

    # Make the desktop window look like a phone while we develop.
    # (This is ignored on a real phone.)
    page.window.width = 390
    page.window.height = 800

    body = ft.Container(expand=True, padding=ft.Padding.all(20))
    act = Actions()
    nav = {"tab": 0}  # remembers which tab is open
    session = {"program_day": None}  # set ONLY when a workout is opened from My 30-Day Plan (never saved)

    def show_screen(index: int):
        """Show one of the 4 main tabs."""
        session["program_day"] = None
        nav["tab"] = index
        nav_bar.visible = True
        nav_bar.selected_index = index
        if index == 0:
            body.content = build_home_screen(page, act)
        elif index == 1:
            body.content = build_workouts_screen(page, act)
        elif index == 2:
            body.content = build_progress_screen(page, act)
        else:
            body.content = build_profile_screen(page, act)
        page.update()

    def show_workout_detail(workout: dict, back=None, program_day=None):
        """Show the workout detail screen. Back returns to the tab (or the plan) you came from.
        program_day is given only when the workout was opened from a day of My 30-Day Plan."""
        session["program_day"] = program_day
        back_index = nav["tab"]
        go_back = back if back is not None else (lambda: show_screen(back_index))
        nav_bar.visible = True
        body.content = build_workout_detail_screen(
            page,
            workout,
            on_back=lambda e: go_back(),
            on_start=lambda e: show_workout_player(workout, back_index, back),
        )
        page.update()

    def show_workout_player(workout: dict, back_index: int, back=None):
        """Show the workout player. The bottom bar is hidden while training."""
        nav_bar.visible = False
        body.content = build_workout_player_screen(
            page,
            workout,
            on_exit=lambda: show_workout_detail(workout, back, session["program_day"]),
            on_finish=on_workout_finished,
        )
        page.update()

    def show_plan(back=None):
        """My 30-Day Plan. Tapping a workout day opens the normal workout detail screen.
        Back goes to Home, or to `back` when the plan was opened from another screen."""
        session["program_day"] = None
        nav_bar.visible = True
        body.content = build_plan_screen(
            page,
            on_back=lambda e: back() if back else show_screen(0),
            on_open_workout=lambda workout: show_workout_detail(workout, back=lambda: show_plan(back), program_day=workout.get("program_day")),
        )
        page.update()

    def show_fitness_plan():
        """Fitness Plan (opened from Profile). Read-only summary of the saved plan setup."""
        session["program_day"] = None
        nav_bar.visible = True
        body.content = build_fitness_plan_screen(
            page,
            on_back=lambda e: show_screen(3),
            on_view_plan=lambda: show_plan(back=show_fitness_plan),
            on_refresh=show_fitness_plan,
        )
        page.update()

    def show_onboarding():
        """The first-launch questions. The bottom bar is hidden until they are done."""
        nav_bar.visible = False
        body.content = build_onboarding_screen(
            page,
            on_complete=apply_onboarding,
            on_done=finish_onboarding,
        )
        page.update()

    def finish_onboarding():
        """Answers are saved: open Home."""
        show_screen(0)
        toast(page, "Welcome to FitLife 🎉")

    def start_app():
        """Onboarding for new users, otherwise straight to Home."""
        if DATA.get("onboarding_completed"):
            show_screen(0)
        else:
            show_onboarding()

    def on_workout_finished(workout: dict, seconds: int, sets: int):
        """Save the finished workout, then go Home."""
        DATA["history"].insert(
            0,
            {
                "date": date.today().isoformat(),
                "name": workout["name"],
                "seconds": max(60, seconds),
                "sets": sets,
            },
        )
        # If this workout was opened from a day of My 30-Day Plan, complete that day too.
        program_day = session.get("program_day")
        session["program_day"] = None
        finished_day = None
        if program_day is not None and complete_program_day(program_day, workout):
            finished_day = program_day
        save_data()
        show_screen(0)
        toast(page, "Workout saved 🎉" if finished_day is None else f"Workout saved 🎉  Day {finished_day} complete ✅")

    # Connect the actions that screens can call.
    act.go_tab = show_screen
    act.open_workout = show_workout_detail
    act.refresh = lambda: show_screen(nav["tab"])
    act.start_app = start_app
    act.open_plan = show_plan
    act.open_fitness_plan = show_fitness_plan
    act.open_plan_workout = lambda workout: show_workout_detail(workout, program_day=workout.get("program_day"))

    nav_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=CARD_COLOR,
        indicator_color=ACCENT,
        on_change=lambda e: show_screen(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER_OUTLINED, selected_icon=ft.Icons.FITNESS_CENTER, label="Workouts"),
            ft.NavigationBarDestination(icon=ft.Icons.SHOW_CHART_OUTLINED, selected_icon=ft.Icons.SHOW_CHART, label="Progress"),
            ft.NavigationBarDestination(icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label="Profile"),
        ],
    )
    page.navigation_bar = nav_bar

    page.add(ft.SafeArea(content=body, expand=True))
    start_app()


ft.run(main)