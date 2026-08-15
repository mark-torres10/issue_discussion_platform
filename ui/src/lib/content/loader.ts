/**
 * Server-side loaders for participant UI copy and sample session YAML.
 *
 * Run from `ui/`:
 * ``uv`` is not used here; run ``npm test -- src/lib/content/loader.test.ts``.
 */
import "server-only";

import { readFileSync } from "node:fs";
import path from "node:path";
import { parse as parseYaml } from "yaml";
import type {
  AiPersona,
  SessionRules,
  SessionStatus,
  StudyIssue,
  StudySession,
} from "@/lib/types/session";

const UI_COPY_PATH = path.join(process.cwd(), "content/ui-copy.yaml");
const SESSION_CONTENT_PATH = path.join(
  process.cwd(),
  "content/sessions/demo-campus-speech-001.yaml",
);

const SESSION_STATUSES = new Set<SessionStatus>([
  "active",
  "completed",
  "expired",
  "paused",
  "invalid",
]);

export interface StatusCopy {
  title: string;
  body: string;
}

export interface UiCopy {
  metadata: {
    title: string;
    description: string;
  };
  layout: {
    skipToContent: string;
    headerBrand: string;
    openSampleSession: string;
  };
  home: {
    eyebrow: string;
    heading: string;
    body: string;
    step1: string;
    step2: string;
    step3: string;
    step4: string;
    openSampleSession: string;
    unavailablePrefix: string;
    expiredLinkLabel: string;
    completedLinkLabel: string;
    pausedLinkLabel: string;
  };
  introduction: {
    eyebrow: string;
    heading: string;
    body: string;
    issueHeading: string;
    meetAiHeading: string;
    assignedPositionLabel: string;
    noteTranscript: string;
    noteConsent: string;
    noteHeadphones: string;
    continueButton: string;
  };
  audioCheck: {
    heading: string;
    body: string;
    modeGroupLabel: string;
    voiceLabel: string;
    textLabel: string;
    headphonesHint: string;
    enableMicrophone: string;
    inputLevelLabel: string;
    micStatusPrefix: string;
    micReadySuffix: string;
    playTestSound: string;
    speakerHeard: string;
    speakerNotConfirmed: string;
    textModeHint: string;
    errorTitle: string;
    testToneError: string;
    startDiscussion: string;
    continueWithText: string;
  };
  conversation: {
    loading: string;
    almostCompleteTitle: string;
    almostCompleteBody: string;
    microphoneIssueTitle: string;
    continueWithText: string;
    captionsHidden: string;
    endDialogTitle: string;
    endDialogDescription: string;
    keepTalking: string;
    endConversationConfirm: string;
    discussionIssueLabel: string;
    endConversationButton: string;
    elapsedPrefix: string;
    connected: string;
    reconnecting: string;
    microphoneOn: string;
    microphoneMuted: string;
    microphone: string;
    micColorHint: string;
    unmute: string;
    mute: string;
    stopAiAudio: string;
    switchToText: string;
    switchToVoice: string;
    hideCaptions: string;
    showCaptions: string;
    reportConnectionProblem: string;
    typeYourResponse: string;
    sendMessageAriaLabel: string;
    send: string;
    voiceStateReady: string;
    voiceStateListening: string;
    voiceStateThinking: string;
    voiceStateSpeaking: string;
    voiceStateMuted: string;
    voiceStateReconnecting: string;
  };
  complete: {
    loading: string;
    heading: string;
    savedBody: string;
    savingBody: string;
    timeLimitTitle: string;
    timeLimitBody: string;
    saveInProgressTitle: string;
    saveInProgressBody: string;
    savedTitle: string;
    savedDescription: string;
    nextStepLabel: string;
    retrySave: string;
  };
  unavailable: {
    expired: StatusCopy;
    completed: StatusCopy;
    paused: StatusCopy;
    invalid: StatusCopy;
    backHome: string;
  };
  notFound: {
    heading: string;
    body: string;
    backHome: string;
  };
}

function readYamlFile(filePath: string): unknown {
  let rawText: string;
  try {
    rawText = readFileSync(filePath, "utf8");
  } catch {
    throw new Error(`Missing content file: ${filePath}`);
  }

  try {
    return parseYaml(rawText);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid YAML in ${filePath}: ${detail}`);
  }
}

function requireMapping(
  value: unknown,
  sourcePath: string,
  keyPath: string,
): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${sourcePath}: missing required key '${keyPath}'`);
  }
  return value as Record<string, unknown>;
}

function requireString(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  key: string,
): string {
  const fullPath = keyPath ? `${keyPath}.${key}` : key;
  const value = mapping[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${sourcePath}: missing required key '${fullPath}'`);
  }
  return value;
}

function requireNumber(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  key: string,
): number {
  const fullPath = `${keyPath}.${key}`;
  const value = mapping[key];
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(`${sourcePath}: missing required key '${fullPath}'`);
  }
  return value;
}

function requireBoolean(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  key: string,
): boolean {
  const fullPath = `${keyPath}.${key}`;
  const value = mapping[key];
  if (typeof value !== "boolean") {
    throw new Error(`${sourcePath}: missing required key '${fullPath}'`);
  }
  return value;
}

function requireStringList(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  key: string,
): string[] {
  const fullPath = `${keyPath}.${key}`;
  const value = mapping[key];
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`${sourcePath}: missing required key '${fullPath}'`);
  }
  for (const [index, entry] of value.entries()) {
    if (typeof entry !== "string" || entry.length === 0) {
      throw new Error(
        `${sourcePath}: missing required key '${fullPath}[${index}]'`,
      );
    }
  }
  return value as string[];
}

function requireChildMapping(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  key: string,
): Record<string, unknown> {
  const fullPath = keyPath ? `${keyPath}.${key}` : key;
  return requireMapping(mapping[key], sourcePath, fullPath);
}

function requireStatusCopy(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
): StatusCopy {
  return {
    title: requireString(mapping, sourcePath, keyPath, "title"),
    body: requireString(mapping, sourcePath, keyPath, "body"),
  };
}

function parseStringGroup<T extends Record<string, string>>(
  mapping: Record<string, unknown>,
  sourcePath: string,
  keyPath: string,
  keys: readonly (keyof T & string)[],
): T {
  const result: Record<string, string> = {};
  for (const key of keys) {
    result[key] = requireString(mapping, sourcePath, keyPath, key);
  }
  return result as T;
}

/**
 * Parse and validate shared UI copy from a YAML document.
 *
 * Parameters
 * ----------
 * raw
 *     Parsed YAML root value.
 * sourcePath
 *     File path included in validation errors.
 *
 * Returns
 * -------
 * UiCopy
 *     Validated shared screen copy.
 *
 * Raises
 * ------
 * Error
 *     When a required key is missing or has the wrong type.
 */
export function parseUiCopy(raw: unknown, sourcePath: string): UiCopy {
  const root = requireMapping(raw, sourcePath, "(root)");
  const metadata = requireChildMapping(root, sourcePath, "", "metadata");
  const layout = requireChildMapping(root, sourcePath, "", "layout");
  const home = requireChildMapping(root, sourcePath, "", "home");
  const introduction = requireChildMapping(root, sourcePath, "", "introduction");
  const audioCheck = requireChildMapping(root, sourcePath, "", "audioCheck");
  const conversation = requireChildMapping(root, sourcePath, "", "conversation");
  const complete = requireChildMapping(root, sourcePath, "", "complete");
  const unavailable = requireChildMapping(root, sourcePath, "", "unavailable");
  const notFound = requireChildMapping(root, sourcePath, "", "notFound");

  return {
    metadata: parseStringGroup(metadata, sourcePath, "metadata", [
      "title",
      "description",
    ]),
    layout: parseStringGroup(layout, sourcePath, "layout", [
      "skipToContent",
      "headerBrand",
      "openSampleSession",
    ]),
    home: parseStringGroup(home, sourcePath, "home", [
      "eyebrow",
      "heading",
      "body",
      "step1",
      "step2",
      "step3",
      "step4",
      "openSampleSession",
      "unavailablePrefix",
      "expiredLinkLabel",
      "completedLinkLabel",
      "pausedLinkLabel",
    ]),
    introduction: parseStringGroup(introduction, sourcePath, "introduction", [
      "eyebrow",
      "heading",
      "body",
      "issueHeading",
      "meetAiHeading",
      "assignedPositionLabel",
      "noteTranscript",
      "noteConsent",
      "noteHeadphones",
      "continueButton",
    ]),
    audioCheck: parseStringGroup(audioCheck, sourcePath, "audioCheck", [
      "heading",
      "body",
      "modeGroupLabel",
      "voiceLabel",
      "textLabel",
      "headphonesHint",
      "enableMicrophone",
      "inputLevelLabel",
      "micStatusPrefix",
      "micReadySuffix",
      "playTestSound",
      "speakerHeard",
      "speakerNotConfirmed",
      "textModeHint",
      "errorTitle",
      "testToneError",
      "startDiscussion",
      "continueWithText",
    ]),
    conversation: parseStringGroup(conversation, sourcePath, "conversation", [
      "loading",
      "almostCompleteTitle",
      "almostCompleteBody",
      "microphoneIssueTitle",
      "continueWithText",
      "captionsHidden",
      "endDialogTitle",
      "endDialogDescription",
      "keepTalking",
      "endConversationConfirm",
      "discussionIssueLabel",
      "endConversationButton",
      "elapsedPrefix",
      "connected",
      "reconnecting",
      "microphoneOn",
      "microphoneMuted",
      "microphone",
      "micColorHint",
      "unmute",
      "mute",
      "stopAiAudio",
      "switchToText",
      "switchToVoice",
      "hideCaptions",
      "showCaptions",
      "reportConnectionProblem",
      "typeYourResponse",
      "sendMessageAriaLabel",
      "send",
      "voiceStateReady",
      "voiceStateListening",
      "voiceStateThinking",
      "voiceStateSpeaking",
      "voiceStateMuted",
      "voiceStateReconnecting",
    ]),
    complete: parseStringGroup(complete, sourcePath, "complete", [
      "loading",
      "heading",
      "savedBody",
      "savingBody",
      "timeLimitTitle",
      "timeLimitBody",
      "saveInProgressTitle",
      "saveInProgressBody",
      "savedTitle",
      "savedDescription",
      "nextStepLabel",
      "retrySave",
    ]),
    unavailable: {
      expired: requireStatusCopy(
        requireChildMapping(unavailable, sourcePath, "unavailable", "expired"),
        sourcePath,
        "unavailable.expired",
      ),
      completed: requireStatusCopy(
        requireChildMapping(
          unavailable,
          sourcePath,
          "unavailable",
          "completed",
        ),
        sourcePath,
        "unavailable.completed",
      ),
      paused: requireStatusCopy(
        requireChildMapping(unavailable, sourcePath, "unavailable", "paused"),
        sourcePath,
        "unavailable.paused",
      ),
      invalid: requireStatusCopy(
        requireChildMapping(unavailable, sourcePath, "unavailable", "invalid"),
        sourcePath,
        "unavailable.invalid",
      ),
      backHome: requireString(unavailable, sourcePath, "unavailable", "backHome"),
    },
    notFound: parseStringGroup(notFound, sourcePath, "notFound", [
      "heading",
      "body",
      "backHome",
    ]),
  };
}

function parseIssue(
  mapping: Record<string, unknown>,
  sourcePath: string,
): StudyIssue {
  return {
    title: requireString(mapping, sourcePath, "issue", "title"),
    summary: requireString(mapping, sourcePath, "issue", "summary"),
  };
}

function parseAiPersona(
  mapping: Record<string, unknown>,
  sourcePath: string,
): AiPersona {
  return {
    displayName: requireString(mapping, sourcePath, "aiPersona", "displayName"),
    shortIntroduction: requireString(
      mapping,
      sourcePath,
      "aiPersona",
      "shortIntroduction",
    ),
    assignedPosition: requireString(
      mapping,
      sourcePath,
      "aiPersona",
      "assignedPosition",
    ),
    avatarSrc: requireString(mapping, sourcePath, "aiPersona", "avatarSrc"),
    avatarAlt: requireString(mapping, sourcePath, "aiPersona", "avatarAlt"),
    isAiLabel: requireString(mapping, sourcePath, "aiPersona", "isAiLabel"),
  };
}

function parseRules(
  mapping: Record<string, unknown>,
  sourcePath: string,
): SessionRules {
  return {
    durationMinutes: requireNumber(
      mapping,
      sourcePath,
      "rules",
      "durationMinutes",
    ),
    warningBeforeEndSeconds: requireNumber(
      mapping,
      sourcePath,
      "rules",
      "warningBeforeEndSeconds",
    ),
    allowInterrupt: requireBoolean(
      mapping,
      sourcePath,
      "rules",
      "allowInterrupt",
    ),
    showExactRemainingTime: requireBoolean(
      mapping,
      sourcePath,
      "rules",
      "showExactRemainingTime",
    ),
    completionNextStep: requireString(
      mapping,
      sourcePath,
      "rules",
      "completionNextStep",
    ),
  };
}

/**
 * Parse and validate a study session document from YAML.
 *
 * Parameters
 * ----------
 * raw
 *     Parsed YAML root value.
 * sourcePath
 *     File path included in validation errors.
 *
 * Returns
 * -------
 * StudySession
 *     Validated sample session configuration.
 *
 * Raises
 * ------
 * Error
 *     When a required key is missing or has the wrong type.
 */
export function parseSessionContent(
  raw: unknown,
  sourcePath: string,
): StudySession {
  const root = requireMapping(raw, sourcePath, "(root)");
  const statusValue = requireString(root, sourcePath, "", "status");
  if (!SESSION_STATUSES.has(statusValue as SessionStatus)) {
    throw new Error(`${sourcePath}: missing required key 'status'`);
  }

  return {
    sessionId: requireString(root, sourcePath, "", "sessionId"),
    studyWave: requireString(root, sourcePath, "", "studyWave"),
    status: statusValue as SessionStatus,
    issue: parseIssue(
      requireChildMapping(root, sourcePath, "", "issue"),
      sourcePath,
    ),
    aiPersona: parseAiPersona(
      requireChildMapping(root, sourcePath, "", "aiPersona"),
      sourcePath,
    ),
    rules: parseRules(
      requireChildMapping(root, sourcePath, "", "rules"),
      sourcePath,
    ),
    openingAiMessage: requireString(root, sourcePath, "", "openingAiMessage"),
    scriptedAiReplies: requireStringList(
      root,
      sourcePath,
      "",
      "scriptedAiReplies",
    ),
  };
}

/**
 * Load shared participant screen copy from ``content/ui-copy.yaml``.
 *
 * Returns
 * -------
 * UiCopy
 *     Validated shared screen strings.
 *
 * Raises
 * ------
 * Error
 *     When the file is missing, invalid, or missing a required key.
 */
export function loadUiCopy(): UiCopy {
  const raw = readYamlFile(UI_COPY_PATH);
  return parseUiCopy(raw, UI_COPY_PATH);
}

/**
 * Load the sample study session from YAML.
 *
 * Returns
 * -------
 * StudySession
 *     Session for ``demo-campus-speech-001`` with status and id from YAML.
 *
 * Raises
 * ------
 * Error
 *     When the file is missing, invalid, or missing a required key.
 */
export function loadSessionContent(): StudySession {
  const raw = readYamlFile(SESSION_CONTENT_PATH);
  return parseSessionContent(raw, SESSION_CONTENT_PATH);
}
