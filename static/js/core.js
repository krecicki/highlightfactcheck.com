// core.js - Dynamically load other JS files
function loadScript(src) {
  return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
  });
}

// Load scripts without functions
// IMPORTANT: JavaScript filenames are case-sensitive, especially on Linux-based servers.
async function loadScripts() {
  const path = "/static/js/components/"
  try {
      await loadScript(path + 'factCheckinit.js');
      //await loadScript(path + 'factCheck.js');
      //await loadScript(path + 'factCheckmembers.js');
      await loadScript(path + 'factChecksubmit.js');
      await loadScript(path + 'createFactCheckSourceBox.js');
      await loadScript(path + 'createSourceBoxes.js');
      await loadScript(path + 'displayFactCheckDetails.js');
      await loadScript(path + 'fetchFactCheckMetadata.js');
      await loadScript(path + 'highlightText.js');
      await loadScript(path + 'initializeHideShow.js');
      await loadScript(path + 'stripeSubscribe.js');
      await loadScript(path + 'stripPaste.js');
      await loadScript(path + 'pixabayFetch.js')
      await loadScript(path + 'uploadImage.js')
      console.log('All scripts loaded successfully');
  } catch (error) {
      console.error('Error loading script:', error);
  }
}

loadScripts();