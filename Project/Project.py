import random
import pandas as pd
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

API_TOKEN = '8003794444:AAFL-KUQlbCsFFszx6o_mhrYJiSSbthocBI'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

data_path = 'Questions.csv'
questions_data = pd.read_csv(data_path, sep=';', header=None, usecols=[0, 1], names=['Question', 'Answer'])

# Инициализация данных игры
players = {
    1: {"number": 1, "location": "площадь", "tasks": [], "tasks_solved": 0},
    2: {"number": 2, "location": "площадь", "tasks": [], "tasks_solved": 0}
}
game_state = {
    "round": 0,
    "active": False,
    "timer": 300  # Таймер на раунд в секундах (5 минут)
}
locations = ["площадь", "больница", "реанимация", "морг", "кладбище"]

# Клавиатура команд
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/solve")],
        [KeyboardButton(text="/shoot")],
        [KeyboardButton(text="/heal")],
        [KeyboardButton(text="/help")],
        [KeyboardButton(text="/begin")],
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/tasks")],
        [KeyboardButton(text="/status")]
    ],
    resize_keyboard=True
)

def generate_tasks_for_players():
    """Генерация уникальных задач для каждого игрока."""
    task_indices = random.sample(range(len(questions_data)), k=len(players) * 3)  # По 3 задачи на игрока
    for i, player_id in enumerate(players):
        players[player_id]["tasks"] = questions_data.iloc[task_indices[i * 3:(i + 1) * 3]].to_dict("records")

@router.message(Command(commands=['start']))
async def show_start_message(message: Message):
    """Приветственное сообщение."""
    await message.reply("Добро пожаловать в игру! Используйте кнопки для управления.", reply_markup=keyboard)

@router.message(Command(commands=['status']))
async def show_status(message: Message):
    """Показывает текущее состояние всех игроков."""
    players_on_square = [player for player in players.values() if player["location"] == "площадь"]
    if len(players_on_square) == 1:
        winner = players_on_square[0]["number"]
        await message.reply(f"Игрок {winner} побеждает! Игра завершена.", reply_markup=keyboard)
        return

    status = [
        f"Игрок {data['number']}: {data['location']}, задач осталось: {len(data['tasks'])}"
        for player_id, data in players.items()
    ]
    await message.reply("\n".join(status), reply_markup=keyboard)

@router.message(Command(commands=['tasks']))
async def show_tasks(message: Message):
    """Показывает задачи игрока."""
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /tasks <номер игрока>", reply_markup=keyboard)
        return

    player_number = int(args[1])
    if player_number not in players:
        await message.reply("Неверный номер игрока.", reply_markup=keyboard)
        return

    tasks = players[player_number]["tasks"]
    if not tasks:
        await message.reply("У вас нет задач.", reply_markup=keyboard)
        return

    task_message = "\n".join([f"{i+1}. {task['Question']}" for i, task in enumerate(tasks)])
    await message.reply(f"Ваши задачи:\n{task_message}", reply_markup=keyboard)

@router.message(Command(commands=['solve']))
async def solve_task(message: Message):
    """Обрабатывает решение задачи."""
    if not game_state["active"]:
        await message.reply("Раунд завершен. Подождите следующего.", reply_markup=keyboard)
        return

    args = message.text.split()
    if len(args) < 4:
        await message.reply("Использование: /solve <номер игрока> <номер задачи> <ответ>", reply_markup=keyboard)
        return

    player_number, task_number, answer = int(args[1]), int(args[2]), args[3]
    if player_number not in players:
        await message.reply("Неверный номер игрока.", reply_markup=keyboard)
        return

    tasks = players[player_number]["tasks"]
    if 0 < task_number <= len(tasks):
        task = tasks[task_number - 1]
        if task["Answer"].strip().lower() == answer.strip().lower():
            players[player_number]["tasks_solved"] += 1
            await message.reply(f"Игрок {player_number}: задача решена.", reply_markup=keyboard)
        else:
            await message.reply("Неверный ответ.", reply_markup=keyboard)
    else:
        await message.reply("Неверный номер задачи.", reply_markup=keyboard)

@router.message(Command(commands=['shoot']))
async def shoot_player(message: Message):
    """Обрабатывает выстрел игрока."""
    if not game_state["active"]:
        await message.reply("Раунд завершен. Подождите следующего.", reply_markup=keyboard)
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply("Использование: /shoot <номер стреляющего> <номер цели>", reply_markup=keyboard)
        return

    shooter_number, target_number = int(args[1]), int(args[2])
    if shooter_number not in players or target_number not in players:
        await message.reply("Неверный номер игрока.", reply_markup=keyboard)
        return

    if players[shooter_number]["location"] != players[target_number]["location"]:
        await message.reply("Вы можете стрелять только в своей локации.", reply_markup=keyboard)
        return

    if players[target_number]["location"] == "кладбище":
        await message.reply("Игрок на кладбище не может получить урон.", reply_markup=keyboard)
        return

    if players[shooter_number]["tasks_solved"] < 1:
        await message.reply("У вас недостаточно задач для выстрела.", reply_markup=keyboard)
        return

    # Подбрасывание монетки
    coin = random.choice(["орел", "решка"])
    if coin == "орел":
        current_location = players[target_number]["location"]
        next_location_index = min(locations.index(current_location) + 1, len(locations) - 1)
        players[target_number]["location"] = locations[next_location_index]

        await message.reply(f"Выстрел успешен! Игрок {target_number} переместился на уровень {players[target_number]['location']}.", reply_markup=keyboard)
    else:
        await message.reply("Выстрел не удался.", reply_markup=keyboard)

@router.message(Command(commands=['heal']))
async def heal_player(message: Message):
    """Обрабатывает лечение игрока."""
    if not game_state["active"]:
        await message.reply("Раунд завершен. Подождите следующего.", reply_markup=keyboard)
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /heal <номер игрока>", reply_markup=keyboard)
        return

    player_number = int(args[1])
    if player_number not in players:
        await message.reply("Неверный номер игрока.", reply_markup=keyboard)
        return

    if players[player_number]["tasks_solved"] < 2:
        await message.reply("Для лечения требуется решить 2 задачи в этом раунде.", reply_markup=keyboard)
        return

    current_location = players[player_number]["location"]
    previous_location_index = max(locations.index(current_location) - 1, 0)
    players[player_number]["location"] = locations[previous_location_index]
    players[player_number]["tasks_solved"] -= 2

    await message.reply(f"Игрок {player_number} успешно вылечился и переместился на уровень {players[player_number]['location']}.", reply_markup=keyboard)

@router.message(Command(commands=['help']))
async def show_help(message: Message):
    """Выводит список доступных команд."""
    help_text = (
        "/status - Показать состояние игроков\n"
        "/tasks <номер игрока> - Показать задачи игрока\n"
        "/solve <номер игрока> <номер задачи> <ответ> - Решить задачу\n"
        "/shoot <номер стреляющего> <номер цели> - Выстрел в игрока\n"
        "/heal <номер игрока> - Лечение игрока\n"
        "/begin - Начать игру\n"
        "/help - Показать список команд"
    )
    await message.reply(help_text, reply_markup=keyboard)

@router.message(Command(commands=['begin']))
async def begin_game(message: Message):
    """Начинает игру, запускает первый раунд."""
    await message.reply("Игра начинается! Приготовьтесь!", reply_markup=keyboard)
    generate_tasks_for_players()
    await start_round()

async def start_round():
    """Запускает новый раунд."""
    game_state["round"] += 1
    game_state["active"] = True

    # Уведомление о задачах
    for player_id, data in players.items():
        task_message = "\n".join([f"{i+1}. {task['Question']}" for i, task in enumerate(data["tasks"])] )
        await bot.send_message(
            chat_id=-1,  # ID группового чата
            text=f"Игрок {data['number']}, ваши задачи:\n{task_message}\n\nУ вас есть {game_state['timer'] // 60} минут!",
            reply_markup=keyboard
        )

    # Таймер раунда
    await asyncio.sleep(game_state['timer'])
    game_state['active'] = False

    # Проверка победителя
    players_on_square = [player for player in players.values() if player["location"] == "площадь"]
    if len(players_on_square) == 1:
        winner = players_on_square[0]["number"]
        await bot.send_message(
            chat_id=-1,
            text=f"Игрок {winner} побеждает! Игра завершена.",
            reply_markup=keyboard
        )
        return

    await bot.send_message(
        chat_id=-1,
        text=f"Время раунда {game_state['round']} истекло! Завершаем раунд.",
        reply_markup=keyboard
    )
    await start_round()

async def check_round_end():
    """Проверяет, завершен ли раунд."""
    if all(len(player["tasks"]) == 0 for player in players.values()):
        game_state["active"] = False

        # Проверка победителя
        players_on_square = [player for player in players.values() if player["location"] == "площадь"]
        if len(players_on_square) == 1:
            winner = players_on_square[0]["number"]
            await bot.send_message(
                chat_id=-1,
                text=f"Игрок {winner} побеждает! Игра завершена.",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=-1,
                text="Все задачи решены! Завершаем раунд.",
                reply_markup=keyboard
            )
            await start_round()




if __name__ == '__main__':
    dp.include_router(router)
    dp.run_polling(bot)



