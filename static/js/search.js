(function () {
  const input = document.getElementById("qms-search-input");
  const results = document.getElementById("qms-results");
  let timeout;

  if (!input || !results) return;

  input.addEventListener("input", function () {
    clearTimeout(timeout);

    timeout = setTimeout(() => {
      const query = input.value;

      fetch(`?q=${encodeURIComponent(query)}`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      })
      .then(response => response.json())
      .then(data => {
        results.innerHTML = data.html;
      });
    }, 250);
  });
})();
