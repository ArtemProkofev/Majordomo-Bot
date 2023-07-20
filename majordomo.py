import asyncio
import discord
from discord.ext import tasks, commands
import json
from loguru import logger
from config import settings


# ===================== ФУНКЦИИ ==========================

# === Работа с JSON ===

# Создание начальных словарей
async def json_start(guild: discord.guild.Guild):
    path_emoji = 'config/' + str(guild.id) + '_emoji.json'  # Названия эмодзей
    path_roles = 'config/' + str(guild.id) + '_roles.json'  # Роли тех, кто может оперировать ботом
    path_public = 'config/' + str(guild.id) + '_public.json'  # Все публичные каналы, их владельцы, участники
    path_private = 'config/' + str(guild.id) + '_private.json'  # Все приватные каналы, их владельцы, участники
    path_channels = 'config/' + str(guild.id) + '_channels.json'  # Технически важные каналы
    path_categories = 'config/' + str(guild.id) + '_categories.json'  # Названия категорий

    try:
        with open(path_emoji, 'x') as f:
            emoji = {
                'yes': settings['emoji_yes'],
                'no': settings['emoji_no'],
                'bad': settings['emoji_bad']
            }
            json.dump(emoji, f)
    except FileExistsError:
        pass

    try:
        with open(path_roles, 'x') as f:
            roles = settings['roles']
            json.dump(roles, f)
    except FileExistsError:
        pass

    try:
        with open(path_public, 'x') as f:
            public = {
                'kostyl': {}  # TODO: Избавиться потом от этого убожества
            }
            json.dump(public, f)
    except FileExistsError:
        pass

    try:
        with open(path_private, 'x') as f:
            private = {
                'message': {}
            }
            json.dump(private, f)
    except FileExistsError:
        pass

    try:
        with open(path_channels, 'x') as f:  # TODO: Избавиться от каналов вообще, оставить только rooms в path_public
            channels = {
                'rooms': None,
                'lobby': guild.system_channel.id if guild.system_channel else None,
                'tech': None
            }
            json.dump(channels, f)
    except FileExistsError:
        pass

    try:
        with open(path_categories, 'x') as f:
            categories = {
                'public': settings['category_public'],
                'private': settings['category_private']
            }
            json.dump(categories, f)
    except FileExistsError:
        pass


# Чтение канала из словарика, возвращает объект Channel
async def json_read_channel(guild: discord.guild.Guild, name):  # name: {'rooms', 'lobby', 'tech'}
    path_channels = 'config/' + str(guild.id) + '_channels.json'
    with open(path_channels, 'r') as f:
        channels = json.load(f)
        if channels[name]:
            return guild.get_channel(channels[name])
        else:
            return None


# Чтение ID сообщения для создания приватного канала из словарика, возвращает int
async def json_read_private_message(guild: discord.guild.Guild):
    path_private = 'config/' + str(guild.id) + '_private.json'
    with open(path_private, 'r') as f:
        private = json.load(f)
        return private['message']


# Чтение словаря каналов, возвращает полноразмерный словарь
async def json_read_channel_dict(guild: discord.guild.Guild, room_type):  # room_type: {'public', 'private'}
    path_channel = 'config/' + str(guild.id) + f'_{room_type}.json'
    with open(path_channel, 'r') as f:
        channel_dict = json.load(f)
        return channel_dict


# Чтение ролей из словарика, возращает set с именами ролей
async def json_read_roles(guild: discord.guild.Guild):
    path_roles = 'config/' + str(guild.id) + '_roles.json'
    with open(path_roles, 'r') as f:
        roles = json.load(f)
        if roles[0]:
            return set(roles)
        else:
            return None


# Чтение эмоджи из словарика, возращает Emoji
async def json_read_emoji(guild: discord.guild.Guild, name):  # name: {'yes', 'no', 'durka'}
    path_emoji = 'config/' + str(guild.id) + '_emoji.json'
    with open(path_emoji, 'r') as f:
        emoji = json.load(f)
        return discord.utils.get(guild.emojis, name=emoji[name])


# Чтение категории из словарика, возвращает имя категории
async def json_read_categories(guild: discord.guild.Guild, name):  # name: {'public', 'private'}
    path_categories = 'config/' + str(guild.id) + '_categories.json'
    with open(path_categories, 'r') as f:
        categories = json.load(f)
        if categories[name]:
            return categories[name]
        else:
            return None


# Запись канала в словарик
async def json_write_channel(guild: discord.guild.Guild, channel):
    path_channels = 'config/' + str(guild.id) + '_channels.json'
    with open(path_channels, 'r') as f:
        channels = json.load(f)
    channels['rooms'] = channel.id
    with open(path_channels, 'w') as f:
        json.dump(channels, f)


# Запись ID сообщения для создания приватного канала в словарика, в формате int
async def json_write_private_message(guild: discord.guild.Guild, message_id):
    path_private = 'config/' + str(guild.id) + '_private.json'
    with open(path_private, 'r') as f:
        private = json.load(f)
    private.update({'message': message_id})
    with open(path_private, 'w') as f:
        json.dump(private, f)


# Запись нового канала в соответствующий словарик
async def json_write_new_channel(author, channel, room_type):  # room_type: {'public', 'private'}
    path_channel = 'config/' + str(author.guild.id) + f'_{room_type}.json'
    with open(path_channel, 'r') as f:
        channel_dict = json.load(f)
    channel_dict.update({author.id: {'name': channel.name, 'id_room': channel.id, 'members': [], 'voice': None}})
    with open(path_channel, 'w') as f:
        json.dump(channel_dict, f)


# Запись нового участника в соответствующий словарик
async def json_write_member(member, channel, room_type):  # room_type: {'public', 'private'}
    path_channel = 'config/' + str(member.guild.id) + f'_{room_type}.json'
    with open(path_channel, 'r') as f:
        channel_dict = json.load(f)
    user_id = None
    for key in channel_dict.keys():
        if channel_dict[key].get('id_room') == channel.id:
            user_id = key
    if user_id:
        members = channel_dict[user_id]['members']
        members.append(member.id)
        channel_dict[user_id].update({'members': members})
        with open(path_channel, 'w') as f:
            json.dump(channel_dict, f)


# Удаление нового участника из соответствующего словарика. НЕ ПРОТЕСТИРОВАНО
async def json_delete_member(member, channel, room_type):  # room_type: {'public', 'private'}
    path_channel = 'config/' + str(member.guild.id) + f'_{room_type}.json'
    with open(path_channel, 'r') as f:
        channel_dict = json.load(f)
    user_id = None
    for key in channel_dict.keys():
        if channel_dict[key].get('id_room') == channel.id:
            user_id = key
    if user_id:
        members = channel_dict[user_id]['members']
        members.remove(member.id)
        channel_dict[user_id].update({'members': members})
        with open(path_channel, 'w') as f:
            json.dump(channel_dict, f)


# Удаление комнаты из словарика
async def json_delete_channel(channel, room_type):
    path_channel = 'config/' + str(channel.guild.id) + f'_{room_type}.json'
    with open(path_channel, 'r') as f:
        channel_dict = json.load(f)
    user_id = None
    for key in channel_dict.keys():
        if channel_dict[key].get('id_room') == channel.id:
            user_id = key
    if user_id:
        channel_dict.pop(user_id)
        with open(path_channel, 'w') as f:
            json.dump(channel_dict, f)


# Умное получение канала lobby
async def json_get_lobby(guild: discord.guild.Guild):
    lobby = await json_read_channel(guild, 'lobby')
    if lobby is None:
        for channel in guild.channels:
            if bot.user.permissions_in(channel).send_messages:
                return channel
    return lobby


# === Проверки ===

# Проверка, в предназначенном ли для комнат канале написана команда
async def channel_is_room(context):
    channel = await json_read_channel(context.guild, 'rooms')
    result = False
    if channel:
        result = context.channel.id == channel.id
    return result


# Проверка, допустимая ли роль запустила команду
async def role_is_allowed(context):
    roles = await json_read_roles(context.guild)
    if context.author == context.guild.owner \
            or discord.utils.get(context.author.roles, permissions__administrator=True) \
                or discord.utils.find(lambda role: role.name in roles, context.author.roles):
        return True
    log_check_failure(context, 'User doesn\'t have right role')
    return False


# Проверка, роль ли с правами админа запустила команду
async def role_is_admin(context):
    if context.author == context.guild.owner \
            or discord.utils.get(context.author.roles, permissions__administrator=True):
        return True
    log_check_failure(context, 'User is not administrator')
    return False


# Проверка, владеет ли участник комнатой, возвращает None, если нет, и ID комнаты, если да
async def member_is_room_owner(member, room_type):  # room_type: {'public', 'private'}
    channel_dict = await json_read_channel_dict(member.guild, room_type)
    return channel_dict.get(str(member.id),{}).get('id_room')

# Проверка, находится ли участник в комнате, возвращает None, если нет, и ID комнаты, если да
async def member_is_in_room(member, channel, room_type):  # room_type: {'public', 'private'}
    channel_dict = await json_read_channel_dict(member.guild, room_type)
    user_id = None
    for key in channel_dict.keys():
        if channel_dict[key].get('id_room') == channel.id:
            user_id = key
    return member.id in channel_dict[user_id]['members'] # TODO: Добавить обработу тех случаев, когда в канале нет никого (словарь юзеров = None)


# Проверка, владеет ли участник комнатой с данным именем
async def member_is_owner_by_name(member, name, room_type):  # room_type: {'public', 'private'}
    channel_dict = await json_read_channel_dict(member.guild, room_type)
    channel_id = 0
    for key in channel_dict.keys():
        if channel_dict[key].get('name') == name:
            channel_id = channel_dict[key]['id_room']
    return channel_id == await member_is_room_owner(member, 'public')


# === Логоёбство ===

# Старт логов и запись, что бот запущен
async def log_start(guild):
    logger.add(f"logs/file_{guild.id}.log",
               format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
               level="INFO",
               rotation="7 days",
               retention="14 days",
               filter=lambda record: record["extra"].get("name") == guild.id)
    exec(f'logger_{guild.id} = logger.bind(name={guild.id})')
    exec(f'logger_{guild.id}.debug("SESSION STARTED in {guild.name}")')


# Запись, что команда совершена. Декоратор. ВСЕГДА ДОЛЖЕН ИДТИ ПОСЛЕДНИМ
def log_command(func):
    async def log_create(context, *args, **kwargs):
        exec(f'logger_{context.channel.guild.id} = logger.bind(name={context.channel.guild.id})')
        exec(f'logger_{context.channel.guild.id}.info("Command {context.command.name} invoked ' +
             f'by {context.author.name} in #{context.channel.name}")')
        await func(context, *args, **kwargs)
    return log_create


# Запись о неудачной попытке инвокации команды
def log_check_failure(context, reason):
    if isinstance(context, discord.ext.commands.Context):
        exec(f'logger_{context.channel.guild.id} = logger.bind(name={context.channel.guild.id})')
        exec(f'logger_{context.channel.guild.id}.error("Failed to invoke command {context.command.name} ' +
             f'by {context.author.name} in #{context.channel.name}. Reason: {reason}")')


# Запись о неудачной попытке создать комнату
def log_room_create_failure(member, reason):
    exec(f'logger_{member.guild.id} = logger.bind(name={member.guild.id})')
    exec(f'logger_{member.guild.id}.error("Failed to create room by {member.name}. Reason: {reason}")')


# Запись об удачной попытке создать комнату
def log_room_create_success(member, channel):
    exec(f'logger_{member.guild.id} = logger.bind(name={member.guild.id})')
    exec(f'logger_{member.guild.id}.success("Successfully created room named #{channel.name} by {member.name}. ID: {channel.id}")')


# Запись об удалении комнаты
def log_room_deleted(member, channel):
    exec(f'logger_{member.guild.id} = logger.bind(name={member.guild.id})')
    exec(f'logger_{member.guild.id}.success("Deleted room named #{channel.name} because of {member.name}. ID: {channel.id}")')


# Запись о том, что участника приняли/выкинули из комнаты
def log_member_change(member, channel, event): # event: {'add', 'remove'}
    exec(f'logger_{member.guild.id} = logger.bind(name={member.guild.id})')
    if event == 'add': # TODO: Здесь был match-case
        event = 'added to'
    elif event == 'remove':
        event = 'removed from'
    exec(f'logger_{member.guild.id}.info("User {member.name} has been {event} a channel named #{channel.name}.")')


# === Работа с сообщениями ===

# Парсим сообщение на составляющие
async def parse_message(message):
    content = list(message.content.partition('\n'))
    content[0] = content[0].strip('- *_')
    content[0] = content[0].replace(' ', '-')
    content.pop(1)

    if len(content[0]) > 25:
        await send_error(message.author, 'big_name', message.content)
        return None
    elif len(content[1]) > 400:
        await send_error(message.author, 'big_description', message.content)
        return None
    elif not content[0].replace('-', '').isalnum():
        await send_error(message.author, 'name_not_alnum', message.content)
        return None
    elif content[1] == '':
        await send_error(message.author, 'no_description', message.content)
        return None
    elif content[1].find('\n') != -1:
        await send_error(message.author, 'excess_description', message.content)
        return None
    else:
        return content


# Парсим эмбед на составляющие
async def parse_embed(message):
    try:
        embed = message.embeds[0]
        content = list()
        content.append(embed.title)
        content.append(embed.description)
        content.append(embed.author.name)
    except IndexError:
        content = None
    return content


# Посылаем сообщение об ошибке в ЛС пользователю
async def send_error(author, error_type, content, channel_name = None):
    error_text = 'Ошибка! Создать комнату на сервере ' + author.guild.name + ' не получилось.\n'
    error_text += '**Причина ошибки**:\n'
    error_text += '`'
    if error_type == 'big_name':  # TODO: Здесь был match-case
        error_text += 'Имя комнаты не должно быть больше 25 знаков.'
    elif error_type == 'big_description':
        error_text += 'Описание комнаты не должно занимать больше 400 знаков.'
    elif error_type == 'name_not_alnum':
        error_text += 'Имя комнаты может состоять только из букв, цифр, пробелов и знаков дефиса.'
    elif error_type == 'no_description':
        error_text += 'Описание комнаты обязательно.'
    elif error_type == 'excess_description':
        error_text += 'Не допускаются красные строки в описании комнаты.'
    elif error_type == 'bad_role':
        error_text += 'У вас нет необходимых ролей.'
    elif error_type == 'room_exists':
        error_text += f'Комната с названием \"{channel_name}\" уже существует.'
    elif error_type == 'user_already_owns_public':
        error_text += f'Вы уже владеете публичной комнатой. Она называется \"{channel_name}\".'
    else:
        error_text += 'Произошла неизвестная ошибка.'
    error_text += '`'
    content_text = 'Ваше сообщение:\n```' + content + '```'
    try:
        await author.send(error_text)
        await author.send(content_text)
    except discord.errors.Forbidden:
        channel = await json_read_channel(author.guild, 'rooms')
        error_text = author.mention + '\n' + error_text
        message = await channel.send(content=error_text, delete_after=10)
    log_room_create_failure(author, error_type)


# Создаём сообщение, через которое можно присоединяться к новым комнатам
async def create_message(message, channel_info):
    embed = discord.Embed(colour=discord.Colour.green(), title=channel_info[0])
    embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
    embed.description = channel_info[1]
    embed.set_footer(text='Используйте реакции, чтобы присоединиться к комнате или уйти из комнаты.')
    file = None
    if message.attachments:
        if message.attachments[0].content_type.startswith('image'):
            attch = message.attachments[0].content_type.split('/')
            file = await message.attachments[0].to_file()
            file.filename = f'teh_image.{attch[1]}'
            embed.set_thumbnail(url=f'attachment://teh_image.{attch[1]}')
    result_message = await message.channel.send(file=file, embed=embed)
    await result_message.add_reaction(await json_read_emoji(message.guild, 'yes'))
    await result_message.add_reaction(await json_read_emoji(message.guild, 'no'))


# Меняем сообщение в связи со смертью комнаты
async def change_message_death(channel):
    rooms = await json_read_channel(channel.guild, 'rooms')
    async for message in rooms.history(limit=200):
        if message.author == bot.user and message.embeds:
            parsed_message = await parse_embed(message)
            if parsed_message[0].lower() == channel.name:
                embed = message.embeds[0]
                embed.colour = discord.Colour.red()
                embed.description += '\n\n**КОМНАТА БЫЛА УДАЛЕНА**'
                file = None
                if message.attachments:
                    if message.attachments[0].content_type.startswith('image'):
                        attch = message.attachments[0].content_type.split('/')
                        file = await message.attachments[0].to_file()
                        file.filename = f'teh_image.{attch[1]}'
                        embed.set_thumbnail(url=f'attachment://teh_image.{attch[1]}')
                await message.edit(attachments=None, embed=embed)
                return


# Создаём приветственное сообщение
async def create_welcome_message(member, channel):
    rooms_channel = await json_read_channel(channel.guild, 'rooms')
    embed = discord.Embed(colour=discord.Colour.teal(), title=f'Добро пожаловать в комнату {channel.name.upper()}')
    embed.set_author(name=member.name, icon_url=member.avatar_url)
    description = 'Поздравляю с созданием комнаты!\n\n'
    description += f'Люди смогут присоединяться к ней или уходить, нажимая эмоджи в канале {rooms_channel.mention}.\n'
    description += 'Даже создатель комнаты не может управлять тем, кто приходит или уходит. Это публичная комната.\n'
    embed.description = description
    delete_text = f'Чтобы удалить комнату, напишите здесь: {bot.user.mention}, удали <имя_комнаты>. В данном случае заклинание ' + \
        f'будет звучать так: {bot.user.mention}, удали {channel.name}.'
    embed.add_field(name='Удаление комнаты', value=delete_text)

    await channel.send(embed=embed)


# === Работа с комнатами ===

# Создаём комнату на сервере, возвращает Channel
async def create_channel(author, name, room_type): # room_type: {'public', 'private'}
    category_name = await json_read_categories(author.guild, room_type)
    if not discord.utils.get(author.guild.categories, name=category_name):
        await author.guild.create_category(name=category_name)
    category = discord.utils.get(author.guild.categories, name=category_name)
    overwrites = {
        author.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        author: discord.PermissionOverwrite(view_channel=True)
    }
    channel = await category.create_text_channel(name=name,overwrites=overwrites)

    await json_write_new_channel(author, channel, room_type)
    log_room_create_success(author, channel)

    return channel


# Удаляет комнату с сервера, возвращает True или False
async def delete_channel(message, name):
    category = None
    for room_type in ['public', 'private']:
        room_dict = await json_read_channel_dict(message.guild, room_type)
        for key in room_dict.keys():
            if room_dict[key].get('id_room') == message.channel.id:
                category = room_type
                break

    if not category:
        return False

    if message.channel.id == await member_is_room_owner(message.author, category) \
            or await role_is_admin(message):
        if name == message.channel.name:
            await message.send('**ЭТА КОМНАТА САМОУНИЧТОЖИТСЯ ЧЕРЕЗ 30 СЕКУНД**\nЧтобы предотвратить удаление, напишите "Отмена".')

            def check(msg):
                return msg.channel == message.channel and msg.author == message.author and msg.content.lower() in ['отмена', 'отмена!', 'отмена.']

            async def countdown(i, m):
                for j in range(i,0,-1):
                    if j <= 5:
                        await m.send(f'**{j}**')
                    await asyncio.sleep(1)

            try:
                countdown = bot.loop.create_task(countdown(30, message))
                await bot.wait_for('message', check=check, timeout=30)
                countdown.cancel()
                await message.send('*Самоуничтожение приостановлено.*')
            except asyncio.TimeoutError:
                await asyncio.sleep(0.5)
                await message.channel.delete()
                await json_delete_channel(message.channel, category)
                log_room_deleted(message.author, message.channel)
                return True
    return False


# Добавляем участника в канал
async def add_member (member, channel, room_type, json=True):
    await channel.set_permissions(member, view_channel=True)
    if json:
        await json_write_member(member, channel, room_type)
    log_member_change(member, channel, 'add')


# Убираем участника из канала
async def remove_member (member, channel, room_type, json=True):
    await channel.set_permissions(member, view_channel=False)
    if json:
        await json_delete_member(member, channel, room_type)
    log_member_change(member, channel, 'remove')


# ========== ТЕЛО БОТА И НАЧАЛЬНАЯ НАСТРОЙКА =============

if __name__ == '__main__':
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=settings['prefix'], intents=intents)

# ===================== КОМАНДЫ ==========================

    # Пинг
    @bot.command(name='Ping', aliases=['ping', 'ping!', 'Ping!', 'пинг', 'Пинг', 'пинг!', 'Пинг!', 'пинг.', 'Пинг.'])
    @commands.check(role_is_allowed)
    @log_command
    async def ping(ctx):
        if ctx.invoked_with in {'ping', 'Ping', 'ping!', 'Ping!'}:
            await ctx.send(f'Pong')
        else:
            await ctx.send(f'Понг')

    # Привет
    @bot.command(name='Hi', aliases=['Привет', 'привет', 'Привет!', 'привет!', 'Привет.', 'привет.'])
    @commands.check(role_is_allowed)
    @log_command
    async def hello(ctx):
        author = ctx.message.author
        channel = ctx.message.channel

        file = discord.File("data/cat_dress.jpg", filename="cat_dress.jpg")

        answer = f'Приветствую, {author.mention}!'
        if await role_is_admin(ctx):
            answer = f'Здравствуйте, хозяин {author.mention}.'

        await channel.send(answer, file=file)

    # Помощь
    @bot.command(name='Help', aliases=['Помощь', 'помощь', 'Помощь.', 'помощь.'])
    @commands.check(role_is_allowed)
    @log_command
    async def halp(ctx):
        channel = ctx.message.channel

        embed_hi = discord.Embed(colour=discord.Colour.purple())
        file_avatar = discord.File("data/cat_dress.jpg", filename="cat_dress.jpg")
        embed_hi.set_thumbnail(url='attachment://cat_dress.jpg')
        embed_hi.description = 'Приветствую, господа. Я отвечаю за комнаты на этом сервере.\n' \
            + 'Комнаты бывают двух типов: публичные и приватные.\n' \
            + 'Список публичных комнат доступен всем, и каждый сам решает, хочет он присутствовать в комнате или нет.\n' \
            + 'Приватные комнаты остаются тайной, пока их владелец не пригласит вас.\n' \
            + 'Итак, как создать одну из таких и что с ними делать?'

        rooms = await json_read_channel(ctx.guild, 'rooms')
        emoji_yes = await json_read_emoji(ctx.guild, 'yes')
        emoji_no = await json_read_emoji(ctx.guild, 'no')

        embed_public = discord.Embed(colour=discord.Colour.gold(), title='Публичные комнаты')
        public_description = 'Объявления обо всех публичных комнатах '
        if rooms:
            public_description += f'появляются в канале {rooms.mention}. '
        else:
            public_description += 'будут появляться в специальном канале, когда ваш администратор его назначит. '
        public_description += f'Нажатие {emoji_yes} откроет вам двери в комнату, а нажатие {emoji_no} поможет уйти.\n\n' \
            + 'В этом же канале создаются новые комнаты. Чтобы это сделать, нужно отправить туда сообщение, состоящее всего из двух строк.\n\n' \
            + 'На первой из них напишите название комнаты, но не длиннее 25 символов и состоящее только из букв, цифр, пробелов и, возможно, дефисов.\n' \
            + 'На второй строке непременно напишите описание, чтобы люди знали, что ожидать от вашей комнаты. Оно должно быть не больше 200 символов длиной!\n\n' \
            + 'К сообщению можно приложить картинку. Готово!\n' \
            + 'После отправки в канале появится новое объявление, а вам откроется доступ к свежесозданной комнате. ' \
            + 'Создатель имеет право удалить собственную комнату навсегда.'
        embed_public.description = public_description

        embed_private = discord.Embed(colour=discord.Colour.orange(), title='Приватные комнаты')
        embed_private.description = '*Раздел находится в разработке. Не переключайтесь!*'

        embed_commands = discord.Embed(colour=discord.Colour.dark_red(), title='Специальные команды')
        embed_commands.description = 'Ко мне можно обращаться напрямую, но тогда перед командой __обязательно__ должно стоять моё упоминание ' \
            + f'(вот такое: {bot.user.mention}).\n\n' \
            + '**Команды для всех**\n' \
            + f'`Пинг` — Так можно понять, на плаву ли я ещё!\n' \
            + f'`Привет` — Со мной можно и поздороваться.\n' \
            + f'`Помощь` — Вызов этой самой команды.\n\n' \
            + '**Команды для администратора**\n' \
            + f'`Назначить` — Назначает канал, в котором написана, в канал для публичных комнат.\n' \
            + f'`Спи` — Отключает меня в случае чего-то непредвиденного.\n\n' \
            + '**Команды для владельцев комнат**\n' \
            + f'`Удали <канал_нейм>` — Удаляет канал, в котором написана. Имя канала должно быть написано правильно!'

        with open("data/cat_maid.jpg", "rb") as img:
            img_byte = img.read()
            webhook = await channel.create_webhook(name=bot.user.name, avatar=img_byte)
        await webhook.send(embeds=[embed_hi, embed_public, embed_private, embed_commands], file=file_avatar)
        await webhook.delete()

    # Узнать, какие каналы выбрал юзер
    @bot.command(name='Check', aliases=['check', 'Проверь', 'проверь', 'Проверить', 'проверить.'])
    @commands.check(role_is_allowed)
    @log_command
    async def check(ctx, name):
        summ = 0
        user = ctx.guild.get_member_named(name)
        answer = f'{user.mention} (**{user.name}**)\n'
        ownership = await member_is_room_owner(user, 'public')
        if ownership:
            answer += f'Владеет: {ctx.guild.get_channel(ownership).name}\n'
            summ += 1
        channel_dict = await json_read_channel_dict(ctx.guild, 'public')
        answer += 'Состоит:'
        for key in channel_dict.keys():
            if key == 'kostyl':
                continue
            channel = ctx.guild.get_channel(channel_dict[key]["id_room"])
            if await member_is_in_room(user, channel, 'public'):
                answer += f'\n- {channel.name}'
                summ += 1
        if answer[-8:] == 'Состоит:':
            answer += ' [Нигде не состоит]'
        else:
            answer += f'\nВсего: {summ}'
        await ctx.message.channel.send(answer)

        
    
    # Назначить канал
    @bot.command(name='Set_Rooms', aliases=['set_rooms', 'Назначить', 'назначить', 'Назначить.', 'назначить.'])
    @commands.check(role_is_admin)
    @log_command
    async def rooms(ctx):
        await json_write_channel(ctx.guild, ctx.channel)
        await ctx.message.add_reaction('🍆')
        await ctx.send(f"Канал {ctx.channel.mention} назначен каналом для публичных комнат.",
                               delete_after=5)
        await ctx.message.delete(delay=5)


    # Удалить комнату
    @bot.command(name='Delete', aliases=['delete', 'Удали', 'удали', 'Удали.', 'удали.'])
    @commands.check(role_is_allowed)
    @log_command
    async def delete(ctx, name):
        name = name.rstrip('.')
        if await delete_channel(ctx, name):
            await change_message_death(ctx.channel)


    # Команда сверки
    @bot.command(name='Revise', aliases=['revise', 'Сверка', 'сверка'])
    @commands.check(role_is_allowed)
    @log_command
    async def revise(ctx):
        rooms_channel = await json_read_channel(ctx.guild, 'rooms')
        new_file = {'kostyl': {}}
        if rooms_channel:
            async for message in rooms_channel.history(limit=200):
                if bot.user == message.author:
                    embed_parsed = await parse_embed(message)
                    if embed_parsed:
                        channel = discord.utils.get(message.guild.channels, name=embed_parsed[0].lower())
                        if channel:
                            new_file.update({embed_parsed[2]: {'name': channel.name, 'id_room': channel.id, 'members': [],
                                                             'voice': None}})
                            reaction_list = message.reactions
                            for reaction in reaction_list:
                                if reaction.emoji == await json_read_emoji(message.guild, 'yes'):
                                    async for user in reaction.users():
                                        if user == bot.user:
                                            continue
                                        members = new_file[embed_parsed[2]]['members']
                                        members.append(user.id)
                                        new_file[embed_parsed[2]].update({'members': members})

                                if reaction.emoji == await json_read_emoji(message.guild, 'no'):
                                    async for user in reaction.users():
                                        if user == bot.user:
                                            continue
                                        members = new_file[embed_parsed[2]]['members']
                                        if user.id in members:
                                            members.remove(user.id)
                                            new_file[embed_parsed[2]].update({'members': members})
                                        try:
                                            await message.remove_reaction(await json_read_emoji(message.guild, 'yes'), user)
                                        except AttributeError:
                                            pass
                                        await message.remove_reaction(await json_read_emoji(message.guild, 'no'), user)

                            path = 'config/' + str(message.guild.id) + '_new_public.json'
                            with open(path, 'w') as f:
                                json.dump(new_file, f)
            answer = await ctx.message.reply(content='Йей, готово!')
            await answer.delete(delay=1)
            await ctx.message.delete(delay=1)

    # Команда сверки
    @bot.command(name='Update', aliases=['update', 'Обнови', 'обнови', 'Обнови.', 'обнови.'])
    @commands.check(role_is_allowed)
    @log_command
    async def update(ctx):
        path_channel = 'config/' + str(ctx.guild.id) + f'_public.json'
        with open(path_channel, 'r') as f:
            channel_dict = json.load(f)

        for key in channel_dict.keys():
            if key == 'kostyl':
                continue
            channel = ctx.guild.get_channel(channel_dict[key]["id_room"])

            for id_member in channel_dict[key]["members"]:
                member = ctx.guild.get_member(id_member)
                if member:
                    await channel.set_permissions(member, view_channel=True)
            creator = ctx.guild.get_member(int(key))
            if member:
                await channel.set_permissions(creator, view_channel=True)


        answer = await ctx.message.reply(content='Готово, десу!')
        await answer.delete(delay=1)
        await ctx.message.delete(delay=1)


    # Завершение работы
    @bot.command(name='Death',
                 aliases=['Умри', 'умри', 'Спи', 'спи', 'Спи.', 'спи.'])
    @commands.check(role_is_admin)
    @log_command
    async def death(ctx):
        channel = ctx.message.channel
        await channel.send(f'<:_anonfilly_crying:827805996809191424>')
        await bot.close()

# ==================== ДЕЙСТВИЯ ==========================

    # При запуске бота: проверить наличие словарей, отчитаться
    @bot.event
    async def on_ready():
        for guild in bot.guilds:
            await json_start(guild)
            await log_start(guild)
        channel = bot.get_channel(827612846950973520)
        await channel.send('Готов вкалывать!')

    # Реагируем на команды, создаём сообщения для комнат
    @bot.event
    async def on_message(message):
        if bot.user == message.author:
            return

        if isinstance(message.channel, discord.DMChannel) or isinstance(message.channel, discord.GroupChannel):
            return

        # Создание сообщения в канале Rooms со всеми проверками
        if await channel_is_room(message):
            if not await role_is_allowed(message):
                await send_error(message.author, 'bad_role', message.content)
            else:
                message_parsed = await parse_message(message)
                if message_parsed:
                    analogy = discord.utils.get(message.guild.channels, name=message_parsed[0].lower()) #TODO: Починить это говно!
                    try:
                        if analogy.category:
                            if analogy.category.name == settings['archive_name']:
                                analogy = None
                    except AttributeError:
                        analogy = None
                    if analogy:
                        await send_error(message.author, 'room_exists', message.content, message_parsed[0].lower())
                    else:
                        if await member_is_room_owner(message.author, 'public'):
                            channel_dict = await json_read_channel_dict(message.guild, 'public')
                            channel_name = message.guild.get_channel(channel_dict[str(message.author.id)]['id_room']).name
                            await send_error(message.author, 'user_already_owns_public', message.content, channel_name=channel_name)
                        else:
                            newborn_channel = await create_channel(message.author, message_parsed[0].lower(), 'public')
                            await create_message(message, message_parsed)
                            await create_welcome_message(message.author, newborn_channel)
            await message.delete()

        await bot.process_commands(message)


    # Реагируем на проставленные эмоджи, добавляем/убираем из комнат
    @bot.event
    async def on_raw_reaction_add(payload):
        if payload.member == bot.user:
            return

        message = await payload.member.guild.get_channel(payload.channel_id).fetch_message(payload.message_id)

        if await channel_is_room(message) and bot.user == message.author:
            message_info = await parse_embed(message)
            channel = discord.utils.get(message.guild.channels, name=message_info[0].lower())

            if not await member_is_owner_by_name(payload.member, message_info[0].lower(), 'public'):

                if payload.emoji == await json_read_emoji(message.guild, 'yes'):
                    await add_member(payload.member, channel, 'public')
                    try:
                        await message.remove_reaction(await json_read_emoji(message.guild, 'no'), payload.member)
                    except AttributeError:
                        pass

                if payload.emoji == await json_read_emoji(message.guild, 'no'):
                    if await member_is_in_room(payload.member, channel, 'public'):
                        await remove_member(payload.member, channel, 'public')
                    try:
                        await message.remove_reaction(await json_read_emoji(message.guild, 'yes'), payload.member)
                    except AttributeError:
                        pass
                    await message.remove_reaction(payload.emoji, payload.member)
            else:
                await message.remove_reaction(payload.emoji, payload.member)  # TODO: Переписать, чтоб не трогало невинные реакции


    # Реагируем на убранные эмоджи, убираем из комнат
    @bot.event
    async def on_raw_reaction_remove(payload):
        if payload.member == bot.user:
            return

        member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
        message = await member.guild.get_channel(payload.channel_id).fetch_message(payload.message_id)

        if await channel_is_room(message) and bot.user == message.author:
            message_info = await parse_embed(message)
            channel = discord.utils.get(message.guild.channels, name=message_info[0].lower())

            if not await member_is_owner_by_name(member, message_info[0].lower(), 'public'):

                if payload.emoji == await json_read_emoji(message.guild, 'yes'):
                    try:
                        await remove_member(member, channel, 'public')
                    except ValueError:
                        pass

                try:
                    await message.remove_reaction(await json_read_emoji(message.guild, 'no'), payload.member)
                except AttributeError:
                    pass


    # Когда человек присоединяется, закидываем его в комнаты, где он должен быть
    @bot.event
    async def on_member_join(member): # TODO: Следить не за прибытием человека, а за изменением ролей
        for room_type in ['public', 'private']:
            room_dict = await json_read_channel_dict(member.guild, room_type)
            for key in room_dict.keys():
                if member.id in room_dict[key].get('members',[]):
                    channel = member.guild.get_channel(room_dict[key]['id_room'])
                    await add_member(member, channel, room_type, json=False)
            owned_room = await member_is_room_owner(member, room_type)
            if owned_room:
                room = bot.get_channel(owned_room)
                await add_member(member, room, room_type, json=False)


# ================== ЗАПУСК БОТА =========================

    bot.run(settings['token'])
