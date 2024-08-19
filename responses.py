from random import choice, randint

def get_response(user_input: str) -> str:
  lowered = user_input.lower()
  print('yes')
  if lowered == '':
    return 'Error: Message Empty'
  elif 'hello' in lowered:
      return 'Hello!'
  else: return 'Rude'