# Data Model Extractor

Alarm.com started using more aggressive static bundling and minification in early 2025. Prior to this, their webapp's entire data model was published unminified -- code comments and all -- making reverse engineering simple. Post-minification, not so much.

The scripts in this folder are quick-and-dirty LLM-generated tools for extracting the Alarm.com webapp's data model from their minified frontend. The results aren't as good as pre-minification: code comments are gone and dependencies are harder to follow.

## Scripts

### scrape-ember.js

Dumps all JavaScript modules loaded by the Ember application at ```https://www.alarm.com/web/system/home``` in a readable format, preserving their original module paths. Each dumped file includes structured metadata such as model attributes, relationships, class inheritance, and method definitions. The result is a static, analyzable snapshot of the app's internal module system

### convert-to-python.js

Generates Python dataclasses from the Ember.js models extracted by ```scrape-ember.js```, including attributes and stubbed method signatures with type hints. The output mirrors the original module structure and helps add new components to pyalarmdotcomajax by providing a clear, structured reference.

## Usage

### Setup
1. Install NodeJS and NPM.
2. Install puppeteer using npm: ```npm install puppeteer```

### Execution
1. Launch Chrome with remote debugging enabled. In Windows PowerShell, the command is
    ```pwsh
    & 'C:\Program Files\Google\Chrome\Application\chrome.exe' --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-devtools-profile"
    ```
    This opens an instance of Chrome that can be controlled by a NodeJS script.
2. In that Chrome instance, log into Alarm.com and get to your dashboard. Ensure that your browser's URL bar shows ```https://www.alarm.com/web/system/home```. _Subsequent steps must be completed before your session expires._
3. Open a command prompt in the same directory as these scripts.
4. Run the scrape-ember.js script first: ```node scrape-ember.js.```
5. After that script has completed, run convert-to-python.js: ```node convert-to-python.js```

## Browser Console Tools

Random browser console snippets to help extract Ember.js models from the Alarm.com website.

### Expose Ember as Global Variable

```js
window.Ember = require('ember').default;
```

This make the ```Ember``` object available for use in the console.

### Dump all Ember Modules

```js
Object.entries(require.entries).forEach(([name]) => {
  try {
    const mod = require(name);
    console.log(name, mod);
  } catch (e) {
    console.warn(`Skipping ${name}:`, e.message);
  }
});
```
