package com.mitramed.controller;

import com.mitramed.service.AiClientService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class MainController {

    @Autowired
    private AiClientService aiService;

    @GetMapping("/")
    public String index(Model model) {
        // Dados iniciais para o Dashboard (KPIs)
        model.addAttribute("totalPacientes", 150); // Aqui depois chamaremos o DB
        return "index";
    }

    @PostMapping("/analisar")
    public String analisar(@RequestParam String prompt, Model model) {
        String resposta = aiService.buscarRespostaIA(prompt);
        model.addAttribute("respostaIA", resposta);
        model.addAttribute("totalPacientes", 150);
        return "index";
    }
}