import { access, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDirectory, "..");
const appRouterDirectories = [resolve(projectRoot, "src/app"), resolve(projectRoot, "app")];

async function directoryExists(path) {
  try {
    await access(path);
    return (await stat(path)).isDirectory();
  } catch {
    return false;
  }
}

async function verifyProjectRoot() {
  for (const appDirectory of appRouterDirectories) {
    if (await directoryExists(appDirectory)) {
      return;
    }
  }

  throw new Error(
    "Could not find an App Router directory. Expected frontend/src/app or frontend/app under the project root."
  );
}

async function main() {
  await verifyProjectRoot();
  process.chdir(projectRoot);

  const wslInfo = getWslInfo(projectRoot);
  if (wslInfo) {
    const forwardedArgs = globalThis.__PROJECT_ARGS__ ?? process.argv.slice(2);
    const shellCommand = buildShellCommand(wslInfo.wslProjectRoot, forwardedArgs);
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

  const nextBin = resolve(projectRoot, "node_modules/next/dist/bin/next");
  const command = process.execPath;
  const forwardedArgs = globalThis.__PROJECT_ARGS__ ?? process.argv.slice(2);
  const args = [nextBin, ...forwardedArgs];

  const child = spawn(command, args, {
    cwd: projectRoot,
    env: process.env,
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
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
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

function buildShellCommand(projectRootPath, args) {
  const commandLine = ["node", "./node_modules/next/dist/bin/next", ...args].map(quoteShellArg).join(" ");
  return `cd ${quoteShellArg(projectRootPath)} && ${commandLine}`;
}

function quoteShellArg(value) {
  return `'${String(value).replace(/'/g, `'"'"'`)}'`;
}