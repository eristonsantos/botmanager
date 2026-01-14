// ui/src-tauri/src/main.rs

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, 
    SystemTrayMenuItem
};

// ============================================================================
// CONSTANTS
// ============================================================================

const WORKER_API_URL: &str = "http://127.0.0.1:8765";
const CONFIG_FILE: &str = "worker_config.json";

// ============================================================================
// TYPES
// ============================================================================

#[derive(Debug, Serialize, Deserialize, Clone)]
struct WorkerStatus {
    running: bool,
    worker_name: String,
    version: String,
    has_active_execution: bool,
    current_execution_id: Option<String>,
    current_execution_pid: Option<u32>,
    last_heartbeat: Option<String>,
    stats: Stats,
    config: WorkerConfig,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Stats {
    executions_completed: u32,
    executions_failed: u32,
    started_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct WorkerConfig {
    orchestrator_url: String,
    polling_interval: u32,
    heartbeat_interval: u32,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConfigUpdate {
    orchestrator_url: String,
    api_key: String,
    tenant_id: String,
    worker_name: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct SavedConfig {
    orchestrator_url: String,
    worker_name: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct KillResult {
    killed: bool,
    execution_id: Option<String>,
}

// ============================================================================
// TAURI COMMANDS
// ============================================================================

#[tauri::command]
async fn get_worker_status() -> Result<WorkerStatus, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .get(format!("{}/status", WORKER_API_URL))
        .send()
        .await
        .map_err(|e| format!("Erro ao conectar ao serviço: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Serviço retornou erro: {}", response.status()));
    }
    
    response
        .json::<WorkerStatus>()
        .await
        .map_err(|e| format!("Erro ao processar resposta: {}", e))
}

#[tauri::command]
async fn start_worker() -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .post(format!("{}/start", WORKER_API_URL))
        .send()
        .await
        .map_err(|e| format!("Erro ao iniciar worker: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Erro ao iniciar: {}", response.status()));
    }
    
    Ok("Worker iniciado".to_string())
}

#[tauri::command]
async fn stop_worker() -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .post(format!("{}/stop", WORKER_API_URL))
        .send()
        .await
        .map_err(|e| format!("Erro ao parar worker: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Erro ao parar: {}", response.status()));
    }
    
    Ok("Worker parado".to_string())
}

#[tauri::command]
async fn kill_automation() -> Result<KillResult, String> {
    let client = reqwest::Client::new();
    
    let response = client
        .post(format!("{}/execution/kill", WORKER_API_URL))
        .send()
        .await
        .map_err(|e| format!("Erro ao matar execução: {}", e))?;
    
    if response.status().is_success() {
        let result = response
            .json::<KillResult>()
            .await
            .map_err(|e| format!("Erro ao processar resposta: {}", e))?;
        Ok(result)
    } else {
        Err(format!("Erro ao matar execução: {}", response.status()))
    }
}

#[tauri::command]
async fn save_config(config: ConfigUpdate) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    // Envia para o worker
    let worker_config = serde_json::json!({
        "orchestrator_url": config.orchestrator_url,
        "api_key": config.api_key,
        "tenant_id": config.tenant_id
    });
    
    let response = client
        .post(format!("{}/config", WORKER_API_URL))
        .json(&worker_config)
        .send()
        .await
        .map_err(|e| format!("Erro ao salvar configuração: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Erro ao salvar: {}", response.status()));
    }
    
    // Salva localmente (sem credenciais sensíveis)
    let saved_config = SavedConfig {
        orchestrator_url: config.orchestrator_url,
        worker_name: config.worker_name,
    };
    
    save_local_config(&saved_config)?;
    
    Ok("Configuração salva".to_string())
}

#[tauri::command]
async fn get_config() -> Result<SavedConfig, String> {
    load_local_config()
}

// ============================================================================
// LOCAL CONFIG MANAGEMENT
// ============================================================================

fn get_config_path() -> Result<PathBuf, String> {
    let config_dir = dirs::config_dir()
        .ok_or_else(|| "Não foi possível encontrar diretório de configuração".to_string())?;
    
    let app_config_dir = config_dir.join("RpaWorker");
    
    // Cria diretório se não existir
    fs::create_dir_all(&app_config_dir)
        .map_err(|e| format!("Erro ao criar diretório de configuração: {}", e))?;
    
    Ok(app_config_dir.join(CONFIG_FILE))
}

fn save_local_config(config: &SavedConfig) -> Result<(), String> {
    let config_path = get_config_path()?;
    
    let json = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Erro ao serializar configuração: {}", e))?;
    
    fs::write(&config_path, json)
        .map_err(|e| format!("Erro ao salvar arquivo de configuração: {}", e))?;
    
    Ok(())
}

fn load_local_config() -> Result<SavedConfig, String> {
    let config_path = get_config_path()?;
    
    if !config_path.exists() {
        // Retorna configuração padrão
        return Ok(SavedConfig {
            orchestrator_url: "http://localhost:8000".to_string(),
            worker_name: "RPA-Worker-01".to_string(),
        });
    }
    
    let json = fs::read_to_string(&config_path)
        .map_err(|e| format!("Erro ao ler arquivo de configuração: {}", e))?;
    
    serde_json::from_str(&json)
        .map_err(|e| format!("Erro ao processar configuração: {}", e))
}

// ============================================================================
// SYSTEM TRAY
// ============================================================================

fn create_system_tray() -> SystemTray {
    let show = CustomMenuItem::new("show".to_string(), "Abrir Painel");
    let start = CustomMenuItem::new("start".to_string(), "Iniciar Worker");
    let stop = CustomMenuItem::new("stop".to_string(), "Parar Worker");
    let quit = CustomMenuItem::new("quit".to_string(), "Sair");
    
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(start)
        .add_item(stop)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);
    
    SystemTray::new().with_menu(tray_menu)
}

fn handle_system_tray_event(app: &tauri::AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::MenuItemClick { id, .. } => {
            match id.as_str() {
                "show" => {
                    if let Some(window) = app.get_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "start" => {
                    let app_handle = app.clone();
                    tauri::async_runtime::spawn(async move {
                        match start_worker().await {
                            Ok(_) => println!("Worker iniciado via tray"),
                            Err(e) => eprintln!("Erro ao iniciar worker via tray: {}", e),
                        }
                    });
                }
                "stop" => {
                    let app_handle = app.clone();
                    tauri::async_runtime::spawn(async move {
                        match stop_worker().await {
                            Ok(_) => println!("Worker parado via tray"),
                            Err(e) => eprintln!("Erro ao parar worker via tray: {}", e),
                        }
                    });
                }
                "quit" => {
                    std::process::exit(0);
                }
                _ => {}
            }
        }
        SystemTrayEvent::DoubleClick { .. } => {
            if let Some(window) = app.get_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        _ => {}
    }
}

// ============================================================================
// WINDOW EVENTS
// ============================================================================

fn handle_window_event(event: tauri::GlobalWindowEvent) {
    match event.event() {
        tauri::WindowEvent::CloseRequested { api, .. } => {
            // Minimiza para tray ao invés de fechar
            event.window().hide().unwrap();
            api.prevent_close();
        }
        _ => {}
    }
}

// ============================================================================
// MAIN
// ============================================================================

fn main() {
    let system_tray = create_system_tray();
    
    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(handle_system_tray_event)
        .on_window_event(handle_window_event)
        .invoke_handler(tauri::generate_handler![
            get_worker_status,
            start_worker,
            stop_worker,
            kill_automation,
            save_config,
            get_config
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}