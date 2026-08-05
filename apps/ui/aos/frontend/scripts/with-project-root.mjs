import { access } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDirectory, "..");

async function main() {
  const forwardedArgs = globalThis.__PROJECT_ARGS__ ?? process.argv.slice(2);
  const [command, ...args] = forwardedArgs;

  if (!command) {
    console.error("Usage: node ./scripts/with-project-root.mjs <command> [args...]");
    process.exit(1);
  }

  process.chdir(projectRoot);

  const wslInfo = getWslInfo(projectRoot);
  if (wslInfo) {
    const shellCommand = buildShellCommand(wslInfo.wslProjectRoot, command, args);
    const child = spawn("wsl.exe", ["-d", wslInfo.distro, "--", "bash", "-lc", shellCommand], {
      stdio: "inherit",
    });

    child.on("exit", (code, signal) => {
      if (signal) {
        process.kill(process.pid, signal);
        return;
      }

      process.exit(code ?? 0);
    });

    child.on("error", (error) => {
      console.error(error);
      process.exit(1);
    });

    return;
  }

  const { executable, executableArgs } = resolveCommandInvocation(command, args, projectRoot);

  const child = spawn(executable, executableArgs, {
    cwd: projectRoot,
    env: process.env,
    stdio: "inherit",
    shell: false,
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }

    process.exit(code ?? 0);
  });

  child.on("error", (error) => {
    console.error(error);
    process.exit(1);
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

function getWslInfo(path) {
  const match = /^\\\\wsl\.localhost\\([^\\]+)\\(.*)$/.exec(path);
  if (!match) {
    return null;
  }

  return {
    distro: match[1],
    wslProjectRoot: `/${match[2].replace(/\\/g, "/")}`,
  };
}

function buildShellCommand(projectRootPath, command, args) {
  const { executable, executableArgs } = resolveCommandInvocation(command, args, projectRootPath);
  const commandLine = [executable, ...executableArgs].map(quoteShellArg).join(" ");
  return `cd ${quoteShellArg(projectRootPath)} && ${commandLine}`;
}

function quoteShellArg(value) {
  return `'${String(value).replace(/'/g, `'"'"'`)}'`;
}

function resolveCommandInvocation(command, args, projectRootPath) {
  const entrypoints = {
    eslint: "node_modules/eslint/bin/eslint.js",
    husky: "node_modules/husky/bin.js",
    playwright: "node_modules/@playwright/test/cli.js",
    prettier: "node_modules/prettier/bin/prettier.cjs",
    tsc: "node_modules/typescript/bin/tsc",
    vitest: "node_modules/vitest/vitest.mjs",
  };

  const entrypoint = entrypoints[command];
  if (entrypoint) {
    return { executable: "node", executableArgs: [resolve(projectRootPath, entrypoint), ...args] };
  }

  return { executable: command, executableArgs: args };
}

async function awaitExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}