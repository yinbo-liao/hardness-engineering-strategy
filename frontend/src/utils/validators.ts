export function isValidTaskDescription(desc: string): boolean {
  return desc.trim().length >= 5 && desc.length <= 1024;
}

export function isValidTaskType(type: string): boolean {
  return ["code", "test", "review", "deploy", "fix"].includes(type);
}

export function isValidRiskLevel(level: string): boolean {
  return ["low", "medium", "high", "critical"].includes(level);
}
