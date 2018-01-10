export const DROP_IN_CATEGORY = 'DROP_IN_CATEGORY';

export function dropInCategory() {

  const payload = "Dropped!";

  return {
    type: DROP_IN_CATEGORY,
    payload: payload
  };
}
