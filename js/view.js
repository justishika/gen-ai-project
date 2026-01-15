import { state } from "./model.js";

const metaDataParent = document.querySelector(".meta-data-container");
const summaryParent = document.querySelector(".summary-container");
const button1 = document.querySelector("#button1");
const button2 = document.querySelector("#button2");
const search = document.querySelector("#search-input");

export const displayMetaData = function () {
    clear(metaDataParent);
    const markup = `
        <div id="video-title">${state.title}</div>
        <div id="video-thumbnail"><img src="${state.thumbnailUrl}"></div>
    `;
    metaDataParent.insertAdjacentHTML("afterbegin", markup);
};

export const getVideoUrl = function () {
    return search.value;
};

const clear = function (element) {
    element.innerHTML = "";
};

export const renderSpinnerMetaData = function () {
    clear(metaDataParent);
    const markup = `<div class="spinner"></div>`;
    metaDataParent.insertAdjacentHTML("afterbegin", markup);
};

export const renderSpinnerSummary = function () {
    clear(summaryParent);
    const markup = `
        <div class="summary">
            <h2>Video Summary:</h2>
            <div class="spinner-container">
                <div class="spinner"></div>
            </div>
        </div>`;
    summaryParent.insertAdjacentHTML("afterbegin", markup);
};

export const renderSummary = function () {
    clear(summaryParent);

    // Better formatting for summary text
    // Note: Summary comes from our trusted backend, so we can safely format it
    let formattedSummary = state.summary;

    // Handle headings (lines that are all caps or start with ## or are short and bold-looking)
    formattedSummary = formattedSummary.replace(/^##\s*(.+)$/gm, '<h3 class="summary-heading">$1</h3>');
    formattedSummary = formattedSummary.replace(/^###\s*(.+)$/gm, '<h4 class="summary-subheading">$1</h4>');

    // Handle markdown-style bold text (**text**)
    formattedSummary = formattedSummary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Handle italic text (*text*)
    formattedSummary = formattedSummary.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');

    // Split into lines for processing
    const lines = formattedSummary.split('\n');
    const processedLines = [];
    let inParagraph = false;
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (!line) {
            // Empty line - close paragraph/list if open
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            continue;
        }

        // Check for markdown headings
        if (line.match(/^##\s+(.+)$/)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            processedLines.push(`<h3 class="summary-heading">${line.replace(/^##\s+/, '')}</h3>`);
        }
        // Check for markdown subheadings
        else if (line.match(/^###\s+(.+)$/)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            processedLines.push(`<h4 class="summary-subheading">${line.replace(/^###\s+/, '')}</h4>`);
        }
        // Check for section headings with Roman numerals (I., II., III., IV., V., etc.)
        else if (line.match(/^([IVX]+)\.\s+(.+)$/i)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            const match = line.match(/^([IVX]+)\.\s+(.+)$/i);
            processedLines.push(`<h3 class="summary-heading">${match[1]}. ${match[2]}</h3>`);
        }
        // Check for numbered lists (1., 2., etc.)
        else if (line.match(/^(\d+)\.\s+(.+)$/)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            const match = line.match(/^(\d+)\.\s+(.+)$/);
            processedLines.push(`<div class="summary-item"><strong class="summary-number">${match[1]}.</strong> <span class="summary-content">${match[2]}</span></div>`);
        }
        // Check for bullet points with asterisk (*)
        else if (line.match(/^\*\s+(.+)$/)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (!inList) {
                processedLines.push('<ul class="summary-list">');
                inList = true;
            }
            const match = line.match(/^\*\s+(.+)$/);
            processedLines.push(`<li class="summary-list-item">${match[1]}</li>`);
        }
        // Check for bullet points with dash (-)
        else if (line.match(/^-\s+(.+)$/)) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (!inList) {
                processedLines.push('<ul class="summary-list">');
                inList = true;
            }
            const match = line.match(/^-\s+(.+)$/);
            processedLines.push(`<li class="summary-list-item">${match[1]}</li>`);
        }
        // Check for lines that look like headings (all caps or bold at start)
        else if (line.match(/^<strong>[^<]+<\/strong>:\s*$/) || (line.length < 60 && line.match(/^[A-Z][A-Z\s:]+$/))) {
            if (inParagraph) {
                processedLines.push('</p>');
                inParagraph = false;
            }
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            processedLines.push(`<h4 class="summary-subheading">${line}</h4>`);
        }
        // Regular text - add to paragraph
        else {
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            if (!inParagraph) {
                processedLines.push('<p class="summary-paragraph">');
                inParagraph = true;
            }
            processedLines.push(line + '<br>');
        }
    }

    // Close last paragraph/list if open
    if (inParagraph) {
        processedLines.push('</p>');
    }
    if (inList) {
        processedLines.push('</ul>');
    }

    formattedSummary = processedLines.join('');

    const markup = `
        <div class="summary">
            <h2>Video Summary:</h2>
            <div class="summary-text">${formattedSummary}</div>
            
            <!-- NER Section -->
            <div class="ner-section">
                <button class="btn-ner-toggle" id="ner-toggle">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
                    </svg>
                    Extract Entities & Facts
                </button>
                
                <div class="ner-container" id="ner-container" style="display: none;">
                    <div class="ner-loading" id="ner-loading" style="display: none;">
                        <div class="spinner-container">
                            <div class="spinner"></div>
                        </div>
                        <p>Analyzing video content...</p>
                    </div>
                    <div class="ner-content" id="ner-content"></div>
                </div>
            </div>
            
            <!-- Q&A Section -->
            <div class="qa-section">
                <button class="btn-qa-toggle" id="qa-toggle">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    Ask Questions About This Video
                </button>
                
                <div class="qa-container" id="qa-container" style="display: none;">
                    <div class="insights-section" id="insights-section">
                        <button class="btn-insights" id="btn-insights">
                            💡 Get Video Insights & Suggested Questions
                        </button>
                        <div id="insights-content"></div>
                    </div>
                    
                    <div class="conversation" id="conversation"></div>
                    
                    <div class="qa-input-section">
                        <div class="qa-input-wrapper">
                            <input 
                                type="text" 
                                id="qa-input" 
                                placeholder="Ask anything about the video..."
                                autocomplete="off"
                            />
                            <button class="btn-send" id="btn-send">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"></path>
                                </svg>
                            </button>
                        </div>
                        <button class="btn-clear-chat" id="btn-clear">Clear Conversation</button>
                    </div>
                </div>
            </div>
        </div>`;

    summaryParent.insertAdjacentHTML("afterbegin", markup);
};

export const renderQAToggle = function (handler) {
    const toggleBtn = document.querySelector("#qa-toggle");
    const qaContainer = document.querySelector("#qa-container");

    if (toggleBtn && qaContainer) {
        toggleBtn.addEventListener("click", function () {
            const isVisible = qaContainer.style.display !== "none";
            qaContainer.style.display = isVisible ? "none" : "block";
            toggleBtn.textContent = isVisible ? "Ask Questions About This Video" : "Hide Q&A";

            // Add icon back
            if (isVisible) {
                toggleBtn.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    Ask Questions About This Video`;
            } else {
                toggleBtn.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M18 6L6 18M6 6l12 12"></path>
                    </svg>
                    Hide Q&A`;
            }
        });
    }
};

export const addQAHandlers = function (askHandler, clearHandler, insightsHandler) {
    renderQAToggle();

    const sendBtn = document.querySelector("#btn-send");
    const qaInput = document.querySelector("#qa-input");
    const clearBtn = document.querySelector("#btn-clear");
    const insightsBtn = document.querySelector("#btn-insights");

    if (sendBtn && qaInput) {
        const handleSend = function () {
            const question = qaInput.value.trim();
            if (question) {
                askHandler(question);
                qaInput.value = "";
            }
        };

        sendBtn.addEventListener("click", handleSend);
        qaInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                handleSend();
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", clearHandler);
    }

    if (insightsBtn) {
        insightsBtn.addEventListener("click", insightsHandler);
    }
};

export const renderQuestion = function (question) {
    const conversation = document.querySelector("#conversation");
    if (!conversation) return;

    const markup = `
        <div class="message user-message">
            <div class="message-content">${escapeHtml(question)}</div>
        </div>
        <div class="message ai-message">
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;

    conversation.insertAdjacentHTML("beforeend", markup);
    conversation.scrollTop = conversation.scrollHeight;
};

export const renderAnswer = function (answer, metrics) {
    const conversation = document.querySelector("#conversation");
    if (!conversation) return;

    const messages = conversation.querySelectorAll(".ai-message");
    const lastMessage = messages[messages.length - 1];

    if (lastMessage) {
        const formattedAnswer = answer
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>");

        let metricsMarkup = '';
        if (metrics) {
            metricsMarkup = `
                <div class="metrics-container" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <div class="metrics-grid">
                        <span class="metric-item" title="Cosine Similarity of Query vs Context">🔍 Retrieval: <strong>${(metrics.retrieval_score * 100).toFixed(1)}%</strong></span>
                        <span class="metric-item" title="Word Overlap (ROUGE-1)">✅ Faithfulness: <strong>${(metrics.faithfulness * 100).toFixed(1)}%</strong></span>
                        <span class="metric-item" title="Cosine Similarity of Question vs Answer">🎯 Relevance: <strong>${(metrics.answer_relevance * 100).toFixed(1)}%</strong></span>
                        <span class="metric-item" title="LLM Coherence Score (0-1)">🧠 Coherence: <strong>${(metrics.coherence * 100).toFixed(0)}%</strong></span>
                        <span class="metric-item" title="Precision of Retrieved Context">📏 Precision: <strong>${(metrics.context_precision * 100).toFixed(1)}%</strong></span>
                        <span class="metric-item" title="Context Recall Proxy">🔄 Recall: <strong>${(metrics.context_recall_proxy * 100).toFixed(0)}%</strong></span>
                        <span class="metric-item" title="Mean Reciprocal Rank">🏆 MRR: <strong>${metrics.mrr.toFixed(2)}</strong></span>
                        <span class="metric-item" title="Generation Time">⏱️ Latency: <strong>${metrics.latency}s</strong></span>
                    </div>
                </div>
            `;
        }

        lastMessage.querySelector(".message-content").innerHTML = formattedAnswer + metricsMarkup;
        conversation.scrollTop = conversation.scrollHeight;
    }
};

export const clearConversation = function () {
    const conversation = document.querySelector("#conversation");
    if (conversation) {
        conversation.innerHTML = "";
    }
};

export const renderInsights = function (insights) {
    const insightsContent = document.querySelector("#insights-content");
    if (!insightsContent) return;

    const formattedInsights = insights
        .replace(/\n/g, "<br>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>");

    insightsContent.innerHTML = `
        <div class="insights-box">
            ${formattedInsights}
        </div>
    `;
};

export const showInsightsLoading = function () {
    const insightsContent = document.querySelector("#insights-content");
    if (insightsContent) {
        insightsContent.innerHTML = `
            <div class="spinner-container">
                <div class="spinner"></div>
            </div>
        `;
    }
};

export const renderError = function (errorMessage) {
    clear(metaDataParent);
    clear(summaryParent);
    const markup = `
        <div class="error">
            <div class="error-text">${errorMessage}</div>
        </div>`;
    metaDataParent.insertAdjacentHTML("afterbegin", markup);
};

export const renderQAError = function (errorMessage) {
    const conversation = document.querySelector("#conversation");
    if (!conversation) return;

    const messages = conversation.querySelectorAll(".ai-message");
    const lastMessage = messages[messages.length - 1];

    if (lastMessage) {
        lastMessage.querySelector(".message-content").innerHTML = `
            <span style="color: #fca5a5;">❌ ${escapeHtml(errorMessage)}</span>
        `;
    }
};

export const scrollToSummary = function () {
    summaryParent.scrollIntoView({ behavior: "smooth", block: "start" });
};

// NER Functions
export const showNERLoading = function () {
    const nerLoading = document.getElementById("ner-loading");
    const nerContent = document.getElementById("ner-content");
    if (nerLoading) nerLoading.style.display = "block";
    if (nerContent) nerContent.innerHTML = "";
};

export const hideNERLoading = function () {
    const nerLoading = document.getElementById("ner-loading");
    if (nerLoading) nerLoading.style.display = "none";
};

export const renderNERData = function (nerData) {
    const nerContent = document.getElementById("ner-content");
    if (!nerContent) return;

    hideNERLoading();

    const { entities, timeline, key_facts, relationships } = nerData;

    let markup = '<div class="ner-display">';

    // Key Facts Section
    if (key_facts) {
        markup += `
            <div class="ner-section-card">
                <h3 class="ner-section-title">💡 Key Insights & Trivia</h3>
                
                ${key_facts.smart_insights && key_facts.smart_insights.length > 0 ? `
                    <div class="smart-insights-list">
                        ${key_facts.smart_insights.map(insight => `
                            <div class="insight-item">
                                <span class="insight-icon">✨</span>
                                <span class="insight-text">${escapeHtml(insight)}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="facts-grid">
                        <div class="fact-item">
                            <span class="fact-label">People Mentioned:</span>
                            <span class="fact-value">${key_facts.people_mentioned || 0}</span>
                        </div>
                        <div class="fact-item">
                            <span class="fact-label">Organizations:</span>
                            <span class="fact-value">${key_facts.organizations || 0}</span>
                        </div>
                        <div class="fact-item">
                            <span class="fact-label">Locations:</span>
                            <span class="fact-value">${key_facts.locations || 0}</span>
                        </div>
                        <div class="fact-item">
                            <span class="fact-label">Dates Mentioned:</span>
                            <span class="fact-value">${key_facts.dates_mentioned || 0}</span>
                        </div>
                    </div>
                `}
                
                ${key_facts.top_people && key_facts.top_people.length > 0 ? `
                    <div class="top-entities">
                        <h4>Top People:</h4>
                        <div class="entity-tags">
                            ${key_facts.top_people.map(p => `<span class="entity-tag person-tag">${escapeHtml(p.name)} (${p.mentions})</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${key_facts.top_organizations && key_facts.top_organizations.length > 0 ? `
                    <div class="top-entities">
                        <h4>Top Organizations:</h4>
                        <div class="entity-tags">
                            ${key_facts.top_organizations.map(o => `<span class="entity-tag org-tag">${escapeHtml(o.name)} (${o.mentions})</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${key_facts.top_locations && key_facts.top_locations.length > 0 ? `
                    <div class="top-entities">
                        <h4>Top Locations:</h4>
                        <div class="entity-tags">
                            ${key_facts.top_locations.map(l => `<span class="entity-tag loc-tag">${escapeHtml(l.name)} (${l.mentions})</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    // Entities Section
    if (entities && Object.keys(entities).length > 0) {
        markup += `
            <div class="ner-section-card">
                <h3 class="ner-section-title">🏷️ Named Entities</h3>
                <div class="entities-grid">
        `;

        for (const [entityType, entityList] of Object.entries(entities)) {
            if (entityList.length > 0) {
                markup += `
                    <div class="entity-category">
                        <h4 class="entity-category-title">${getEntityTypeLabel(entityType)}</h4>
                        <div class="entity-list">
                            ${entityList.slice(0, 10).map(e => `<span class="entity-item">${escapeHtml(e.text)}</span>`).join('')}
                            ${entityList.length > 10 ? `<span class="entity-more">+${entityList.length - 10} more</span>` : ''}
                        </div>
                    </div>
                `;
            }
        }

        markup += `</div></div>`;
    }

    // Timeline Section
    if (timeline && timeline.length > 0) {
        markup += `
            <div class="ner-section-card">
                <h3 class="ner-section-title">📅 Timeline</h3>
                <div class="timeline">
                    ${timeline.slice(0, 10).map(item => `
                        <div class="timeline-item">
                            <div class="timeline-date">${escapeHtml(item.date)}</div>
                            <div class="timeline-context">${escapeHtml(item.context)}</div>
                        </div>
                    `).join('')}
                    ${timeline.length > 10 ? `<div class="timeline-more">+${timeline.length - 10} more dates</div>` : ''}
                </div>
            </div>
        `;
    }

    // Relationships Section
    if (relationships && relationships.length > 0) {
        markup += `
            <div class="ner-section-card">
                <h3 class="ner-section-title">🔗 Relationships</h3>
                <div class="relationships">
                    ${relationships.slice(0, 10).map(rel => `
                        <div class="relationship-item">
                            <div class="relationship-type">${getRelationshipTypeLabel(rel.type)}</div>
                            <div class="relationship-entities">
                                <span class="rel-entity">${escapeHtml(rel.entity1)}</span>
                                <span class="rel-arrow">→</span>
                                <span class="rel-entity">${escapeHtml(rel.entity2)}</span>
                            </div>
                            <div class="relationship-context">${escapeHtml(rel.context)}</div>
                        </div>
                    `).join('')}
                    ${relationships.length > 10 ? `<div class="relationships-more">+${relationships.length - 10} more relationships</div>` : ''}
                </div>
            </div>
        `;
    }

    // Check if we have structured data
    const hasStructuredData = (key_facts || (entities && Object.keys(entities).length > 0) || (timeline && timeline.length > 0) || (relationships && relationships.length > 0));

    if (!hasStructuredData) {
        // Fallback for when LLM returns unstructured text or parsing failed but returned text
        const rawText = nerData.error_text || nerData.text || (typeof nerData === 'string' ? nerData : JSON.stringify(nerData));

        if (rawText && rawText.length > 20) {
            // It's likely a summary or text response
            markup += `
                <div class="ner-section-card">
                    <h3 class="ner-section-title">Analysis Result</h3>
                    <div class="ner-text-fallback">${escapeHtml(rawText)}</div>
                </div>`;
        } else {
            markup += `<div class="error">Unable to extract structured entities. Please try again.</div>`;
        }
    }

    markup += '</div>';
    nerContent.innerHTML = markup;

    // Show the container
    const nerContainer = document.getElementById("ner-container");
    if (nerContainer) {
        nerContainer.style.display = "block";
    }
};

export const addNERHandler = function (handler) {
    const nerToggle = document.getElementById("ner-toggle");
    const nerContainer = document.getElementById("ner-container");

    if (nerToggle && nerContainer) {
        nerToggle.addEventListener("click", function () {
            const isVisible = nerContainer.style.display !== "none";
            if (!isVisible) {
                // Show container and trigger extraction
                nerContainer.style.display = "block";
                showNERLoading();
                handler();
            } else {
                nerContainer.style.display = "none";
            }
        });
    }
};

function getEntityTypeLabel(type) {
    const labels = {
        'PERSON': '👤 People',
        'ORG': '🏢 Organizations',
        'GPE': '🌍 Places',
        'LOC': '📍 Locations',
        'DATE': '📅 Dates',
        'TIME': '⏰ Times',
        'MONEY': '💰 Money',
        'PERCENT': '📊 Percentages',
        'EVENT': '🎉 Events',
        'PRODUCT': '📦 Products',
        'LAW': '⚖️ Laws',
        'LANGUAGE': '🗣️ Languages',
        'NORP': '🌐 Groups'
    };
    return labels[type] || type;
}

function getRelationshipTypeLabel(type) {
    const labels = {
        'PERSON-ORG': 'Person ↔ Organization',
        'PERSON-LOC': 'Person ↔ Location',
        'ORG-LOC': 'Organization ↔ Location'
    };
    return labels[type] || type;
}

export const addHandlerSearch = function (handler) {
    const button1 = document.querySelector("#button1");
    const button2 = document.querySelector("#button2");

    if (button1) {
        button1.addEventListener("click", function (e) {
            e.preventDefault();
            handler('short');
        });
    }

    if (button2) {
        button2.addEventListener("click", function (e) {
            e.preventDefault();
            handler('detailed');
        });
    }
};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}