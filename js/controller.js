import * as model from "./model.js";
import * as view from "./view.js";
import { getVideoId } from "./helper.js";
import "core-js/stable";
import "regenerator-runtime/runtime";

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const normalizeYouTubeUrl = function (url) {
    try {
        const parsed = new URL(url);

        // Handle Shorts → convert to youtu.be
        if (
            parsed.hostname.includes("youtube.com") &&
            parsed.pathname.startsWith("/shorts/")
        ) {
            const videoId = parsed.pathname.split("/shorts/")[1];
            return `https://youtu.be/${videoId}${parsed.search}`;
        }

        // Return unchanged for other URLs
        return url;
    } catch (err) {
        return url;
    }
};

const controlSummary = async function (summaryType = 'short') {
    try {
        // 0. get video URL from view
        const videoUrlRaw = view.getVideoUrl();
        const videoUrl = normalizeYouTubeUrl(videoUrlRaw);

        // 1. get video Id
        const videoId = getVideoId(videoUrl);
        if (!videoId) throw new Error("Please Enter a valid YouTube URL!");

        // 2. Update state
        model.state.videoId = videoId;
        model.clearConversation(); // Clear previous Q&A

        // 3. load spinner for metadata
        view.renderSpinnerMetaData();

        // 4. load metadata
        await model.loadMetaData(videoId);

        // 5. display thumbnail and title
        view.displayMetaData();

        // 6. load spinner for summary
        view.renderSpinnerSummary();

        // 7. scroll to summary
        view.scrollToSummary();

        // 8. get summary from model
        await model.loadSummary(summaryType);

        // 9. Render summary with Q&A section
        view.renderSummary();

        // 10. Add Q&A handlers
        view.addQAHandlers(controlAskQuestion, controlClearConversation, controlLoadInsights);

        // 11. Add NER handler
        view.addNERHandler(controlExtractEntities);

        // 12. scroll to summary again when loaded
        view.scrollToSummary();

    } catch (error) {
        console.log(error);
        view.renderError(error.message);
    }
};

const controlAskQuestion = async function (question) {
    try {
        // Render the question immediately
        view.renderQuestion(question);

        // Get answer from model
        const { answer, metrics } = await model.askQuestion(question);

        // Render the answer
        view.renderAnswer(answer, metrics);

    } catch (error) {
        console.error("Error asking question:", error);

        let errorMessage = "Unable to answer the question. Please try again.";

        if (error.response && error.response.data && error.response.data.data) {
            // Server returned a specific error message
            errorMessage = error.response.data.data;
        } else if (error.message) {
            // General JS error message
            errorMessage = error.message;
        }

        view.renderQAError(`Error: ${errorMessage}`);
    }
};

const controlClearConversation = function () {
    model.clearConversation();
    view.clearConversation();
};

const controlLoadInsights = async function () {
    try {
        view.showInsightsLoading();
        const insights = await model.loadInsights();
        view.renderInsights(insights);
    } catch (error) {
        console.error("Error loading insights:", error);
        view.renderInsights("Unable to generate insights. Please try again.");
    }
};

const controlExtractEntities = async function () {
    try {
        view.showNERLoading();
        const nerData = await model.extractEntities();
        view.renderNERData(nerData);
    } catch (error) {
        console.error("Error extracting entities:", error);
        view.hideNERLoading();
        const nerContent = document.getElementById("ner-content");
        if (nerContent) {
            nerContent.innerHTML = `<div class="error">${escapeHtml(error.message || "Unable to extract entities. Please try again.")}</div>`;
        }
    }
};

const init = function () {
    view.addHandlerSearch(controlSummary);
};

init();