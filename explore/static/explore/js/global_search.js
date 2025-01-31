document.addEventListener('DOMContentLoaded', function () {
    // Add CSS styles
    const style = document.createElement('style');
    style.innerHTML = `
    .search-form{display:flex;justify-content:center}.dropdown{position:relative;width:600px;margin-top:20px}.dropdown-content,.search-input{width:100%;background-color:#fff}@media(max-width:650px){.dropdown{width:100%}}.search-input{display:block;min-width:300px;padding:.575rem .85rem;margin:0;font-family:inherit;font-size:1.25rem;font-weight:400;line-height:1.75;color:#858796;-webkit-appearance:none;-moz-appearance:none;appearance:none;background-clip:padding-box;border:1px solid #858796;border-radius:.85rem;transition:border-color .15s ease-in-out,box-shadow .15s ease-in-out;-webkit-appearance:textfield;outline-offset:-2px}.search-input:focus{color:#858796;background-color:#fff;border-color:#a7b9ef;outline:0;box-shadow:0 0 0 .15rem rgba(78,115,223,.25)}.dropdown-content{display:none;position:absolute;margin-bottom:3rem;min-width:160px;box-shadow:0 8px 16px 0 rgba(0,0,0,.2);z-index:1000;border-bottom:1px solid #ccc}.results-list-container{color:#000;padding:12px 16px;text-decoration:none;display:block;cursor:pointer}.spinner{display:None;width:20px;height:20px;border:3px solid #f3f3f3;border-top:3px solid #3498db;border-radius:50%;animation:1s linear infinite spin;position:absolute;right:40px;top:18px}@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}.results-list{list-style-type:none;padding:0;margin:0;max-height:65vh;overflow-y:auto;border:1px solid #ccc;border-radius:4px;background-color:#fff;position:relative;width:100%}.results-list li{padding:10px;cursor:pointer;display:flex;align-items:center;border-bottom:1px solid #ccc}.results-list li img{width:50px;height:50px;margin-right:10px}.close-popup:hover,.results-list li:hover{background-color:#f0f0f0}.pagination{display:flex;justify-content:center;align-items:center;margin:10px;justify-content:space-between}.close-popup{margin:5px;padding:5px;cursor:pointer;font-size:1.5rem;font-weight:700;width:40px;height:40px;color:red;border-radius:50%;background-color:#fff}.close-popup:disabled{cursor:not-allowed;opacity:.5}.results-count{margin:10px}@media (max-width:600px){.results-list,.results-list-container{max-height:calc(100vh - 132px)}.dropdown-content,.pagination{position:fixed;width:100%;background-color:#fff}.dropdown-content{left:50%;top:50%;transform:translate(-50%,-50%);height:100%;overflow-y:auto;border:1px solid #ccc;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.3);z-index:999}.results-list-container{padding:0}.pagination{bottom:0;left:0;margin:0;padding-bottom:80px;border-top:1px solid #ccc;z-index:1000}}
    `;
    document.head.appendChild(style);

    // Create the selected section and insert it into the element with class search-result
    const searchFormContainer = document.querySelector('.search-form');
    let dropdownDiv;
    let resultsContainer;
    let paginationDiv;
    let closePopupButton;
    let resultsCount;
    if (searchFormContainer) {
        dropdownDiv = document.createElement('div');
        dropdownDiv.classList.add('dropdown');

        const searchInput = document.createElement('input');
        searchInput.id = 'searchQuery';
        searchInput.classList.add('search-input');
        searchInput.setAttribute('autocomplete', 'off');
        searchInput.setAttribute('type', 'search');
        searchInput.setAttribute('name', 'q');
        searchInput.setAttribute('placeholder', 'Search Downstream Marketplace');
        searchInput.setAttribute('required', 'true');

        // Create x to clear search input
        const clearButton = document.createElement('button');
        // clearButton.classList.add('close-popup');
        clearButton.textContent = 'X';
        clearButton.style.display = 'none';
        clearButton.style.position = 'absolute';
        clearButton.style.right = '15px';
        clearButton.style.top = '18px';
        clearButton.style.cursor = 'pointer';
        clearButton.style.backgroundColor = 'white';
        clearButton.style.border = 'none';
        clearButton.style.borderRadius = '50%';
        clearButton.style.width = '20px';
        clearButton.style.height = '20px';
        clearButton.style.fontSize = '1rem';
        clearButton.style.fontWeight = '400';
        clearButton.style.color = '#858796';
        clearButton.addEventListener('click', function () {
            searchInput.value = '';
            clearButton.style.display = 'none';
            hideResultsContainer();
        });
        searchInput.addEventListener('input', function () {
            if (searchInput.value.length > 0) {
                clearButton.style.display = 'block';
            } else {
                clearButton.style.display = 'none';
            }
        });

        const spinnerDiv = document.createElement('div');
        spinnerDiv.classList.add('spinner');
        spinnerDiv.id = 'spinner';

        resultsContainer = document.createElement('div');
        resultsContainer.classList.add('dropdown-content');
        resultsContainer.id = 'results-container';

        const resultsDiv = document.createElement('div');
        resultsDiv.id = 'results';
        resultsDiv.classList.add('results-list-container');

        paginationDiv = document.createElement('div');
        paginationDiv.id = 'pagination';
        paginationDiv.classList.add('pagination');
        paginationDiv.style.display = 'none';

        resultsCount = document.createElement('span');
        resultsCount.classList.add('results-count');
        // Add close button to popup
        closePopupButton = document.createElement('button');
        closePopupButton.id = 'closePopup';
        closePopupButton.classList.add('close-popup');
        closePopupButton.textContent = 'X';
        closePopupButton.addEventListener('click', function () {
            event.preventDefault();
            hideResultsContainer();
        });

        if (window.innerWidth < 600) {
            closePopupButton.style.display = 'block';
        } else {
            closePopupButton.style.display = 'none';
        }
        paginationDiv.appendChild(resultsCount);
        paginationDiv.appendChild(closePopupButton);


        resultsContainer.appendChild(resultsDiv);
        if (window.innerWidth >= 600) {
            resultsContainer.appendChild(paginationDiv);
        }

        dropdownDiv.appendChild(searchInput);
        dropdownDiv.appendChild(spinnerDiv);
        dropdownDiv.appendChild(clearButton);
        dropdownDiv.appendChild(resultsContainer);
        if (window.innerWidth < 600) {
            dropdownDiv.appendChild(paginationDiv);
        }

        searchFormContainer.appendChild(dropdownDiv);
    } else {
        console.error('Element with class search-form not found');
        return;
    }

    const searchForm = document.getElementById('searchForm');
    const searchQuery = document.getElementById('searchQuery');
    const spinner = document.getElementById('spinner');
    const resultsDiv = document.getElementById('results');
    const body = document.getElementsByTagName('body')[0];

    // Add window width listener
    window.addEventListener('resize', function () {
        if (window.innerWidth < 600) {
            dropdownDiv.appendChild(paginationDiv);
            closePopupButton.style.display = 'block';
        } else {
            closePopupButton.style.display = 'none';
            resultsContainer.appendChild(paginationDiv);
        }
    });

    let currentPage = 1;
    let totalResults = 0;
    let savedScrollY = window.scrollY;
    let pagePosition = body.style.position;
    const resultsPerPage = 10;
    function hideResultsContainer() {
        body.style.position = pagePosition;
        window.scrollBy(0, savedScrollY);
        document.getElementById("results-container").scrollTo(0, 0);
        resultsContainer.style.display = 'none';
        paginationDiv.style.display = 'none';
        // make searchQuery bottom border rounded again
        searchQuery.style.borderRadius = '0.85rem';
    }
    function showResultsContainer() {
        // Check if page is mobile
        if (window.innerWidth < 600) {
            // https://forum.bubble.io/t/tutorial-scroll-within-a-popup-without-scrolling-the-page/144153
            let savedScrollY = window.scrollY;
            body.style.position = "fixed";
        }
        resultsContainer.style.display = 'block';
        paginationDiv.style.display = 'flex';
        // make searchQuery bottom border square
        searchQuery.style.borderRadius = '0.85rem 0.85rem 0px 0px';
    }
    // Show the dropdown content when the input is focused
    searchQuery.addEventListener('focus', function () {
        if (totalResults > 0) {
            showResultsContainer();
        }
    });
    // Hide the dropdown content when clicking outside of it
    document.addEventListener('click', function (event) {
        if (!resultsContainer.contains(event.target) && !searchQuery.contains(event.target)) {
            hideResultsContainer();
        }
    });

    // Listen for input changes in the field and send the query to the API. Ensure at least 3 characters are entered and wait 500ms before sending the request.
    function getResults(query) {
        totalResults = 0;
        // Check if query is empty
        if (!query) {
            hideResultsContainer();
            return;
        }
        // Show spinner and disable search button
        spinner.style.display = 'block';


        fetch(`https://api.trydownstream.com/explore/v1/search/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                // Clear previous results
                resultsDiv.innerHTML = '';
                resultsCount.textContent = '';
                showResultsContainer();

                // Display search results
                const resultsList = document.createElement('ul');
                resultsList.classList.add('results-list');

                // Check response returns an error (query is empty)
                if (!data || data.errors) {
                    hideResultsContainer();
                    return;
                }
                // Check response is good, but has no results
                if (!data || !data.main_products || !data.main_product_categories || !data.main_product_category_groups) {
                    const listItem = document.createElement('li');
                    listItem.textContent = 'No results found';
                    resultsList.appendChild(listItem);
                    resultsDiv.appendChild(resultsList);
                    return;
                }

                const allResults = [...data.main_products, ...data.main_product_categories, ...data.main_product_category_groups];
                const totalPages = 1
                totalResults = data.main_products.length + data.main_product_categories.length + data.main_product_category_groups.length;
                data.main_product_categories.forEach(category => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    const image = document.createElement('img');
                    const text = document.createElement('span');
                    // Telehandler = Category (https://portal.trydownstream.com/customer/order/new/product/5c911a3d-6df6-49f1-b0cb-5d246aa52de4/)
                    text.textContent = `Category: ${category.name}`;
                    link.href = `https://portal.trydownstream.com/customer/order/new/product/${category.id}`;
                    image.src = category.icon;
                    // link.target = '_blank';
                    link.appendChild(image);
                    link.appendChild(text);
                    listItem.appendChild(link);
                    resultsList.appendChild(listItem);
                    const categoryProducts = data.main_products.filter(product => product.main_product_category === category.id);
                    categoryProducts.forEach(product => {
                        const listItem = document.createElement('li');
                        listItem.style.paddingLeft = '40px';
                        const link = document.createElement('a');
                        const image = document.createElement('img');
                        const text = document.createElement('span');
                        // 5,000 lbs. 19 ft. Telehandler = Product (https://portal.trydownstream.com/customer/order/new/options/7e75424e-d3c4-4979-af66-a206213685ab/)
                        link.href = `https://portal.trydownstream.com/customer/order/new/options/${product.id}`;
                        if (product.images.length > 0) {
                            image.src = product.images[0];
                        } else {
                            image.src = category.icon;
                        }
                        text.textContent = `${product.name}`;
                        // link.target = '_blank';
                        link.appendChild(image);
                        link.appendChild(text);
                        listItem.appendChild(link);
                        resultsList.appendChild(listItem);
                    });
                });
                data.main_product_category_groups.forEach(group => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    const image = document.createElement('img');
                    const text = document.createElement('span');
                    text.textContent = `All ${group.name}`;
                    // Forklift = Group (https://portal.trydownstream.com/customer/order/new/?q=&group_id=c1b69d34-3134-4e3a-b3de-db005bfdbd65)
                    link.href = `https://portal.trydownstream.com/customer/order/new/?q=&group_id=${group.id}`;
                    image.src = group.icon;
                    // link.target = '_blank';
                    link.appendChild(image);
                    link.appendChild(text);
                    listItem.appendChild(link);
                    resultsList.appendChild(listItem);
                });
                resultsDiv.appendChild(resultsList);

                // Update results count
                resultsCount.textContent = `Showing ${totalResults} results`;
            })
            .catch(error => console.error('Error:', error))
            .finally(() => {
                // Hide spinner and enable search button
                spinner.style.display = 'none';
            });
    }
    let debounceTimeout
    searchQuery.addEventListener('input', function (event) {
        // Only trigger the search if the value is not empty and has more than 1 character and the user has stopped typing.
        // Clear the previous timeout
        clearTimeout(debounceTimeout)
        // Set a new timeout
        debounceTimeout = setTimeout(function () {
            if (!searchQuery.value || searchQuery.value.length > 2) {
                const query = searchQuery.value;
                // event.preventDefault();
                getResults(query);
            }
        }, 500)
    });
});