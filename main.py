# Requires Python 3.7+. Used for type hinting (forward references).
from __future__ import annotations
from typing import Iterator, List, Literal, Tuple, Callable, Union, cast
from requests import post
from concurrent.futures import ThreadPoolExecutor


class Exit:
  '''
  Represents an exit from one location to another.
  '''
  _to: Location
  'The location to which the exit leads.'
  _description: str
  'A description of the exit.'

  def __init__(self, to: Location, description: str) -> None:
    self._to: Location = to
    self._description: str = description

  def get_to(self) -> Location:
    '''
    Returns the location to which the exit leads.
    '''
    return self._to

  def get_description(self) -> str:
    '''
    Returns the description of the exit.
    '''
    return self._description

  def set_to(self, to: Location) -> None:
    '''
    Sets the location to which the exit leads.
    '''
    self._to: Location = to

  def set_description(self, description: str) -> None:
    '''
    Sets the description of the exit.
    '''
    self._description: str = description


class Container:
  '''
  Represents a base container that can hold items.
  '''
  _name: str
  'The name of the container.'
  _description: str
  'The description of the container.'
  _items: List[Item]
  'The items currently stored in the container.'

  def __init__(self, name: str, description: str, items: List[Item]) -> None:
    self._name: str = name
    self._description: str = description
    self._items: List[Item] = items

  def get_name(self) -> str:
    '''
    Returns the name of the container.
    '''
    return self._name

  def get_description(self) -> str:
    '''
    Returns the description of the container.
    '''
    return self._description

  def get_items(self) -> List[Item]:
    '''
    Returns the items in the container.
    '''
    return self._items

  def add_item(self, item: Item) -> None:
    '''
    Adds an item to the container.
    '''
    self._items.append(item)

  def remove_item(self, item: Item) -> None:
    '''
    Removes an item from the container.
    '''
    try:
      # Attempt to remove item from items.
      self._items.remove(item)
    except ValueError:
      # Item not in list. Ignore.
      pass


class Location(Container):
  '''
  Represents a location in the game, linked to other locations via exits.
  Can contain items.
  '''
  _exits: List[Exit]
  'The available exits from the location.'

  def __init__(self, name: str, description: str, exits: List[Exit], items: List[Item]) -> None:
    super().__init__(name, description, items)
    self._exits = exits

  def get_exits(self) -> List[Exit]:
    '''
    Returns the available exits from the location.
    '''
    return self._exits

  def add_exit(self, exit: Exit) -> None:
    '''
    Adds an exit to the location.
    '''
    self._exits.append(exit)


class Room(Location):
  '''
  Represents a room in the game.
  '''
  def __init__(self, name: str, description: str, exits: List[Exit], items: List[Item] = []) -> None:
    super().__init__(name, description, exits, items)


class ItemUse:
  '''
  Represents a use for an item.
  Holds a description of the use and a function to execute when the use is invoked.
  Also contains the virtual location of the item, which is used to determine where the item is when the use is invoked (e.g. which container it belongs to).
  '''
  _name: str
  'The name of the use action.'
  _description: str
  'The description of the use action.'
  __item: Item | None
  'The item associated with the use.'
  _execute: Callable[[], None]
  'The function to execute when the item is used.'
  __destroy_on_execute: bool
  'Whether the item should be destroyed when the use is invoked.'
  _virtual_location: Container | None
  'The virtual location of the item. Used for tracking where the item is when the use is invoked (i.e. to remove it from its container on use).'

  def __init__(self, name: str, description: str, execute: Callable[[], None], destroy_on_execute: bool = False) -> None:
    self._name: str = name
    self._description: str = description
    self.__item: Item | None = None
    self.__destroy_on_execute: bool = destroy_on_execute
    self._virtual_location: Container | None = None
    self._execute: Callable[[], None] = execute

  def set_item(self, item: Item) -> None:
    '''
    Sets the item associated with the use.
    '''
    self.__item: Item = item

  def get_name(self) -> str:
    '''
    Returns the name of the use action.
    '''
    return self._name

  def get_description(self) -> str:
    '''
    Returns the description of the use action.
    '''
    return self._description

  def get_virtual_location(self) -> Container | None:
    '''
    Returns the virtual location of the item.
    '''
    return self._virtual_location

  def set_virtual_location(self, virtual_location: Container) -> None:
    '''
    Sets the virtual location of the item.
    '''
    self._virtual_location: Container = virtual_location

  def execute(self) -> None:
    '''
    Executes the use action.
    '''
    if self.__destroy_on_execute:
      self.destroy()
    self._execute()

  def destroy(self) -> None:
    '''
    Destroys the item.
    '''
    self.get_virtual_location().remove_item(self.__item)

class Item:
  '''
  Represents an item in the game.
  '''
  _name: str
  'The name of the item.'
  _description: str
  'The description of the item.'
  _use: ItemUse
  'The use of the item.'

  def __init__(self, name: str, description: str, use: ItemUse) -> None:
    self._name: str = name
    self._description: str = description
    use.set_item(self)
    self._use: ItemUse = use

  def get_name(self) -> str:
    '''
    Returns the name of the item.
    '''
    return self._name

  def get_description(self) -> str:
    '''
    Returns the description of the item.
    '''
    return self._description

  def get_use(self) -> ItemUse:
    '''
    Returns the use of the item.
    '''
    return self._use


class Fruit(Item):
  '''
  Represents an edible fruit item, that is destroyed when eaten.
  '''
  def __init__(self, name: str) -> None:
    super().__init__(name, f'A juicy {name}.', ItemUse('Eat', f'Eat the {name}.', lambda: print(f'You eat the {name}.'), True))


PlayerAction = Union[
  Tuple[Literal['quit'], None],
  Tuple[Literal['inventory'], None],
  Tuple[Literal['take'], Item],
  Tuple[Literal['go'], Exit]
]
'''
The type used to represent the selected player action and its coreresponding attribute (if applicable) in the selection menu.
Expressed as a tuple, in the format: (action: str, attribute: Any).
'''


class Player(Container):
  '''
  The main, first-person player class.
  '''

  _location: Location | None
  'The current location of the player.'

  def __init__(self, name: str, description: str, items: List[Item]) -> None:
    super().__init__(name, description, items)
    self._location: Location = None

  def get_location(self) -> Location:
    '''
    Returns the current location of the player.
    '''
    return self._location

  def set_location(self, location: Location) -> None:
    '''
    Sets the current location of the player.
    '''
    self._location = location

  def enter_inventory(self) -> None:
    '''
    Opens the selection menu for the player\'s inventory.
    '''
    print('Inventory:')
    print(f'  (1) Close inventory.')
    for i, item in enumerate(self.get_items()):
      print(f'  ({i+2}) {item.get_name()}')
      print(f'    {item.get_description()}')
      print(f'    {item.get_use().get_description()}')
    print('Enter item number to use or 0 to exit:')
    choice: int | None = None
    while not choice:
      try:
        choice = int(input('> '))
        if choice < 1 or choice > len(self.get_items()) + 1:
          choice = None
          raise ValueError
      except ValueError:
        print(f'Invalid choice. Please enter a number between 0 and {len(self.get_items())}.')
    if choice == 1:
      return
    print(choice)
    if not self.get_items()[choice - 2].get_use():
      print('This item has no use.')
      return
    self.get_items()[choice - 2].get_use().execute()

  def print_location(self) -> None:
    '''
    Prints the current location of the player.
    '''
    location: Location = self.get_location()
    print(f'Location: {location.get_name()}')
    print(f'{location.get_description()}')

  def print_and_get_actions(self) -> List[PlayerAction]:
    '''
    Prints the available actions for the player and returns them as a list of PlayerAction tuples.
    '''
    location: Location = self.get_location()
    actions: List[PlayerAction] = [('quit', None), ('inventory', None)]
    print('Actions:')
    print('  (1) Quit')
    print('  (2) Inventory')
    print()
    i = 2
    print('Items:')
    for item in location.get_items():
      i += 1
      print(f'  ({i}) {item.get_name()}')
      print(f'    {item.get_description()}')
      actions.append(('take', item))
    else:
      if i == 2:
        print('  (no available items)')
    print()
    print('Exits:')
    for ex in location.get_exits():
      i += 1
      print(f'  ({i}) {ex.get_to().get_name()}')
      print(f'    {ex.get_description()}')
      actions.append(('go', ex))
    return actions

  def prompt(self) -> None:
    '''
    Prompts the player for an action.
    Refer to: PlayerAction.
    '''
    print('=' * 30)
    self.print_location()
    print()
    actions = self.print_and_get_actions()
    print()
    print('What would you like to do?')
    action: int | None = None
    while not action:
      try:
        action = int(input('> '))
        if action < 1 or action > len(actions):
          action = None
          raise ValueError
      except ValueError:
        print(f'Invalid choice. Please enter a number between 1 and {len(actions)}.')
    action_type, action_object = actions[action - 1]
    match action_type:
      case 'quit':
        print('Goodbye!')
        exit()
      case 'inventory':
        self.enter_inventory()
      case 'take':
        action_object: Item = cast(Item, action_object)
        print(f'You take the {action_object.get_name()}.')
        # Remove item from location.
        self.get_location().remove_item(action_object)
        # Add item to inventory.
        self.add_item(action_object)
        # Set item's virtual location to player.
        action_object.get_use().set_virtual_location(self)
      case 'go':
        action_object: Exit = cast(Exit, action_object)
        print(f'You go to the {action_object.get_to().get_name()}.')
        self.set_location(action_object.get_to())
    self.prompt()


def create_twoway_link(from_location: Location, to_location: Location) -> None:
  '''
  Creates a two-way link between two locations.

  ---
  Example:
  ```
  create_twoway_link(lounge, hall)
  ```
  Creates an exit from the lounge to the hall and vice versa.
  '''
  from_location.add_exit(Exit(to_location, f'Go to the {to_location.get_name()}.'))
  to_location.add_exit(Exit(from_location, f'Go to the {from_location.get_name()}.'))


def ask_gpt(prompt: str) -> str:
  '''
  Ask GPT for a response to a prompt. Using a reverse-engineered API, so may break at any time.
  '''
  return post('https://cyborg.net.au/api/v1/chat', json={
    'content': prompt,
    'variant': 0,
    'id': None
  }).text


if __name__ == '__main__':
  print('Please wait while the game loads...')
  rooms_gpt_responses: Iterator[str]
  'The responses from GPT for the room descriptions. Hardcoded order.'
  with ThreadPoolExecutor() as executor:
    rooms_gpt_responses = executor.map(ask_gpt, [
      'Provide a 75-word description for a lounge. The lounge is homely and dimly lit. There is a door to the hall and a door to the kitchen.',
      'Provide a 75-word description for a kitchen. The kitchen is well-decorated, modern, well-equiped and clean, but lightly used. It\'s clear that the owner rarely uses the kitchen. There is a door to the lounge and a door to the dining room.',
      'Provide a 75-word description for a hall of a house. The hall is a long, narrow hallway with a wooden floor. There is a door to the lounge and a door to the dining room.',
      'Provide a 75-word description for a dining room of a house. Although not large, it is cosy. The dining room has a small fireplace and a cold stone flooring. The morning sun peeks in from the gaps of the shutters. There is a long table with chairs. There is a door leading back to the kitchen and a door leading back to the hall.'
    ])
  rooms_gpt_responses: List[str] = list(rooms_gpt_responses)
  print('Game loaded!')
  # Create rooms.
  crown: Item = Item('Crown', 'A golden crown.', ItemUse('Wear', 'Wear the crown.', lambda: print('You put the crown on your head.'), True))
  lounge: Room = Room('Lounge', rooms_gpt_responses[0], [], [crown])
  mango: Fruit = Fruit('Mango')
  apple: Fruit = Fruit('Apple')
  kitchen: Room = Room('Kitchen', rooms_gpt_responses[1], [], [mango, apple])
  hall: Location = Location('Hall', rooms_gpt_responses[2], [], [])
  diamond: Item = Item('Diamond', 'A shiny diamond. It looks valuable.', ItemUse('Sell', 'Sell the diamond.', lambda: print('You sell the diamond but get scammed.'), True))
  dining_room: Room = Room('Dining Room', rooms_gpt_responses[3], [], [diamond])

  # Create exits.
  create_twoway_link(lounge, hall)
  create_twoway_link(lounge, kitchen)
  create_twoway_link(hall, dining_room)
  create_twoway_link(kitchen, dining_room)

  # Create player.
  print('Enter your name:')
  name = input('> ')
  print(f'Nice to meet you, {name}!')
  player = Player(name, 'You are you.', [])
  player.set_location(lounge)

  # Start game loop.
  player.prompt()
