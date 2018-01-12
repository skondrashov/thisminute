export const DROP_IN_CATEGORY = 'DROP_IN_CATEGORY';

export function dropInCategory(category) {

  const payload = "Dropped in " + category;

  return {
    type: DROP_IN_CATEGORY,
    payload: payload
  };
}
