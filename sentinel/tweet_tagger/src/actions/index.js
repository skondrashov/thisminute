export const DROP_IN_CATEGORY = 'DROP_IN_CATEGORY';

export function dropInCategory(id, category) {

  const payload = "test";
  console.log("Dropped tweet with id " + id + " in category " + category)

  return {
    type: DROP_IN_CATEGORY,
    payload: payload
  };
}
