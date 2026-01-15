const SUPABASE_URL = "https://jcydjrcjwjtjedunziqk.supabase.co";
const SUPABASE_KEY = "sb_publishable_6ExmO6Dun-GiWE39_LKF2g_yYkAuQvo";

const grid = document.getElementById("servicesGrid");
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modalTitle");
const planSelect = document.getElementById("planSelect");
const priceValue = document.getElementById("priceValue");
const buyBtn = document.getElementById("buyBtn");

let servicesMap = {};
let currentService = "";
let currentPlan = "";

// ===== SERVICE DETECT =====
function getService(p){
  const n = p.name.toLowerCase();
  if(n.includes("alfa ushare")) return "Alfa Ushare";
  if(n.includes("netflix")) return "Netflix";
  if(n.includes("shahid")) return "Shahid";
  if(n.includes("osn")) return "OSN";
  return p.name;
}

// ===== ACCOUNT TYPE =====
function getAccountType(p){
  const n = p.name.toLowerCase();
  if(n.includes("full")) return "Full Account";
  return "1 User";
}

// ===== LABEL =====
function getLabel(p){
  if(p.name.toLowerCase().includes("alfa ushare")){
    return p.duration; // 11 GB, 22 GB...
  }
  const type = getAccountType(p);
  return `${type} - ${p.duration}`;
}

// ===== ORDER FOR SHAHID =====
function sortPlans(service, plans){
  if(service === "Shahid"){
    const order = [
      "1 User - 1 Month",
      "1 User - 3 Months",
      "1 User - 1 Year",
      "Full Account - 1 Month",
      "Full Account - 3 Months",
      "Full Account - 1 Year"
    ];
    return plans.sort((a,b)=> order.indexOf(a.label) - order.indexOf(b.label));
  }

  // ===== SORT ALFA USHARE BY GB ASC =====
  if(service === "Alfa Ushare"){
    return plans.sort((a,b)=>{
      const getGB = v => {
        const m = v.label.match(/(\d+)/);
        return m ? parseInt(m[1]) : 0;
      };
      return getGB(a) - getGB(b);
    });
  }

  return plans;
}

async function loadProducts(){
  const res = await fetch(`${SUPABASE_URL}/rest/v1/products?select=*`,{
    headers:{
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`
    }
  });
  const products = await res.json();

  products.forEach(p=>{
    const service = getService(p);
    if(!servicesMap[service]) servicesMap[service] = [];

    servicesMap[service].push({
      ...p,
      label: getLabel(p)
    });
  });

  renderServices();
}

function renderServices(){
  grid.innerHTML = "";
  Object.keys(servicesMap).forEach(service=>{
    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div class="img-box"><img src="${servicesMap[service][0].image}" alt="${service}"></div>
      <span>${service}</span>
    `;
    card.onclick = ()=>openModal(service);
    grid.appendChild(card);
  });
}

function openModal(service){
  currentService = service;
  modalTitle.textContent = service;
  planSelect.innerHTML = "";

  let plans = servicesMap[service];
  plans = sortPlans(service, plans);

  plans.forEach((p,i)=>{
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = p.label;
    planSelect.appendChild(opt);
  });

  updatePrice(service,0);
  modal.classList.remove("hidden");
  planSelect.onchange = e=>updatePrice(service,e.target.value);
}

function updatePrice(service,index){
  const p = servicesMap[service][index];
  currentPlan = p.label;
  priceValue.textContent = p.price;

  const msg = `Hello, I would like to order:%0A${currentService}%0ADuration: ${currentPlan}%0APrice: ${p.price} LBP`;
  buyBtn.href = `https://wa.me/9613177862?text=${msg}`;
}

document.getElementById("closeModal").onclick = ()=>modal.classList.add("hidden");
document.getElementById("cancelBtn").onclick = ()=>modal.classList.add("hidden");

loadProducts();
