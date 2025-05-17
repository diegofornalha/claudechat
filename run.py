#!/usr/bin/env python3
"""
Script para interagir com Claude usando o SessionManager.
Este script permite enviar mensagens, listar conversas e gerenciar sessões.
"""

import sys
import os
import argparse
from claudechat.utils.session_manager import SessionManager

def main():
    parser = argparse.ArgumentParser(description="Interação com Claude via SessionManager")
    
    # Comandos principais
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis")
    
    # Comando para enviar mensagem
    msg_parser = subparsers.add_parser("mensagem", help="Enviar mensagem ao Claude")
    msg_parser.add_argument("texto", help="Texto da mensagem")
    msg_parser.add_argument("-s", "--sessao", help="ID da sessão (opcional)")
    
    # Comando para listar conversas
    list_parser = subparsers.add_parser("listar", help="Listar todas as conversas")
    
    # Comando para mostrar uma conversa
    show_parser = subparsers.add_parser("mostrar", help="Mostrar detalhes de uma conversa")
    show_parser.add_argument("sessao", help="ID da sessão")
    
    # Comando para criar nova conversa
    create_parser = subparsers.add_parser("criar", help="Criar nova conversa")
    create_parser.add_argument("titulo", help="Título da nova conversa")
    
    # Comando para ver tarefas (todos)
    todos_parser = subparsers.add_parser("tarefas", help="Listar tarefas de uma sessão")
    todos_parser.add_argument("sessao", help="ID da sessão")
    
    args = parser.parse_args()
    
    # Inicializar gerenciador de sessões
    session_manager = SessionManager()
    
    # Processar comandos
    if args.comando == "mensagem":
        session_id = args.sessao
        
        # Se não especificou sessão, usa a última ou cria uma nova
        if not session_id:
            conversas = session_manager.get_all_conversations()
            if conversas:
                session_id = conversas[0]['id']
                print(f"Usando sessão existente: {conversas[0]['title']} ({session_id})")
            else:
                title = "Nova Conversa"
                session_id = session_manager.create_new_conversation(title)
                print(f"Criada nova sessão: {title} ({session_id})")
        
        # Adiciona mensagem e mostra resposta
        print(f"Enviando: {args.texto}")
        session_manager.add_message(session_id, "user", args.texto)
        resposta = session_manager.get_conversation(session_id)['messages'][-1]
        print(f"\nResposta do Claude:\n{resposta['content']}")
    
    elif args.comando == "listar":
        conversas = session_manager.get_all_conversations()
        if not conversas:
            print("Nenhuma conversa encontrada.")
            return
        
        print("Conversas disponíveis:")
        for conv in conversas:
            print(f"- {conv['title']} (ID: {conv['id']})")
    
    elif args.comando == "mostrar":
        try:
            conversa = session_manager.get_conversation(args.sessao)
            print(f"Título: {conversa['title']}")
            print(f"ID: {conversa['id']}")
            print(f"Criada em: {conversa['created_at']}")
            print("\nMensagens:")
            for msg in conversa['messages']:
                role = "Você" if msg['role'] == "user" else "Claude"
                print(f"\n[{role}]:")
                print(msg['content'])
        except Exception as e:
            print(f"Erro ao buscar conversa: {e}")
    
    elif args.comando == "criar":
        try:
            session_id = session_manager.create_new_conversation(args.titulo)
            print(f"Nova conversa criada: {args.titulo} (ID: {session_id})")
        except Exception as e:
            print(f"Erro ao criar conversa: {e}")
    
    elif args.comando == "tarefas":
        try:
            todos = session_manager.get_todos(args.sessao)
            if not todos:
                print("Nenhuma tarefa encontrada.")
                return
            
            print(f"Tarefas da sessão {args.sessao}:")
            for todo in todos:
                status = {
                    "pending": "Pendente",
                    "in_progress": "Em andamento",
                    "completed": "Concluída"
                }.get(todo['status'], todo['status'])
                
                priority = {
                    "high": "Alta",
                    "medium": "Média",
                    "low": "Baixa"
                }.get(todo['priority'], todo['priority'])
                
                print(f"- [{status}][{priority}] {todo['content']}")
        except Exception as e:
            print(f"Erro ao buscar tarefas: {e}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()