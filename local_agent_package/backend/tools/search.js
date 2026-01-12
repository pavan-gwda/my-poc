const axios = require("axios");

module.exports = async function searchTool(query) {
  const url = "https://api.duckduckgo.com/?q=" +
              encodeURIComponent(query) +
              "&format=json&no_redirect=1&no_html=1";

  try {
    const response = await axios.get(url);

    const results = (response.data.RelatedTopics || [])
      .filter(item => item.Text)
      .map(item => ({
        title: item.Text,
        link: item.FirstURL
      }));

    return {
      tool: "search",
      success: true,
      results
    };
  } catch (e) {
    return { tool: "search", success: false, error: e.message };
  }
};
