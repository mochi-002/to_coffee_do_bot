import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os, json

# === Load Token ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# === Bot Setup ===
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
DATA_FILE = "todos.json"

# === Data Storage ===
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        todos = json.load(f)
else:
    todos = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(todos, f, indent=2)

# === Helper: progress bar ===
def progress_bar(done, total):
    if total == 0:
        return "No tasks yet!"
    ratio = done / total
    filled = int(ratio * 10)
    bar = "▮" * filled + "▯" * (10 - filled)
    return f"{bar}  {done}/{total} ({int(ratio*100)}%)"

# === Helper: rank system ===
def get_rank(points):
    if points < 5:
        return "🐣 Beginner"
    elif points < 10:
        return "💪 Achiever"
    elif points < 20:
        return "🏆 Task Master"
    else:
        return "🌟 Productivity Legend"

async def check_rank_and_role(interaction, user_id):
    """Check if user earned new role."""
    guild = interaction.guild
    user = interaction.user
    user_data = todos[str(user_id)]

    rank = get_rank(user_data["points"])
    # Ensure role exists
    role_name = "Task Master"
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(name=role_name)

    # Give role if Task Master or above
    if user_data["points"] >= 10 and role not in user.roles:
        await user.add_roles(role)
        await interaction.followup.send(
            f"🎉 Congrats {user.mention}! You’ve earned the **{role_name}** role!"
        )

# === Events ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# === Slash Commands ===
@bot.tree.command(name="todo_add", description="Add a new task")
async def add_task(interaction: discord.Interaction, task: str):
    user = str(interaction.user.id)
    todos.setdefault(user, {"tasks": [], "done": [], "points": 0})
    todos[user]["tasks"].append(task)
    save_data()
    await interaction.response.send_message(f"📝 Task added: **{task}**")

@bot.tree.command(name="todo_list", description="List your tasks and progress")
async def list_tasks(interaction: discord.Interaction):
    user = str(interaction.user.id)
    data = todos.get(user, {"tasks": [], "done": [], "points": 0})
    if not data["tasks"]:
        await interaction.response.send_message("📭 You have no tasks yet.")
        return
    msg = "\n".join([f"{i+1}. {t}" for i, t in enumerate(data["tasks"])])
    prog = progress_bar(len(data["done"]), len(data["tasks"]) + len(data["done"]))
    await interaction.response.send_message(f"📋 **Your Tasks:**\n{msg}\n\n📊 {prog}")

@bot.tree.command(name="todo_done", description="Mark a task as done")
async def done_task(interaction: discord.Interaction, index: int):
    user = str(interaction.user.id)
    await interaction.response.defer()
    if user not in todos or not (0 < index <= len(todos[user]["tasks"])):
        await interaction.followup.send("❌ Invalid task number.")
        return
    task = todos[user]["tasks"].pop(index - 1)
    todos[user]["done"].append(task)
    todos[user]["points"] += 1
    save_data()

    await interaction.followup.send(f"✅ Completed: **{task}**\n🏆 You earned **+1 point!**")

    await check_rank_and_role(interaction, user)

@bot.tree.command(name="todo_remove", description="Remove a task without marking done")
async def remove_task(interaction: discord.Interaction, index: int):
    user = str(interaction.user.id)
    if user not in todos or not (0 < index <= len(todos[user]["tasks"])):
        await interaction.response.send_message("❌ Invalid task number.")
        return
    removed = todos[user]["tasks"].pop(index - 1)
    save_data()
    await interaction.response.send_message(f"🗑️ Removed: **{removed}**")

@bot.tree.command(name="todo_showall", description="(Admin) Show all users' tasks")
async def show_all(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 You must be an admin to use this.")
        return
    if not todos:
        await interaction.response.send_message("📭 No users found.")
        return
    msg = ""
    for user_id, data in todos.items():
        user = await bot.fetch_user(int(user_id))
        rank = get_rank(data.get("points", 0))
        msg += f"**{user.name}** — {rank} ({data['points']} pts)\n"
        if data["tasks"]:
            msg += "\n".join([f"• {t}" for t in data["tasks"]])
        else:
            msg += "No active tasks."
        msg += f"\n📊 {progress_bar(len(data['done']), len(data['tasks']) + len(data['done']))}\n\n"
    await interaction.response.send_message(msg[:1900])

@bot.tree.command(name="todo_rank", description="Show your rank and stats")
async def show_rank(interaction: discord.Interaction):
    user = str(interaction.user.id)
    data = todos.get(user, {"tasks": [], "done": [], "points": 0})
    rank = get_rank(data["points"])
    total = len(data["tasks"]) + len(data["done"])
    prog = progress_bar(len(data["done"]), total)
    await interaction.response.send_message(
        f"🏅 **{interaction.user.name}** — {rank}\n"
        f"⭐ **Points:** {data['points']}\n📊 {prog}"
    )

# === Run ===
bot.run(TOKEN)
