export function labelMatchesSearch(label: string, searchLabels: string[]): boolean {
  return searchLabels.some(
    (search) =>
      label === search || label.startsWith(`${search} `) || search.startsWith(`${label} `),
  )
}
